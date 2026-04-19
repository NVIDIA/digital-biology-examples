# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""Regression tests for MultiEndpointClient reliability fixes.

Each test in this module pins a specific bug discovered in
``MultiEndpointClient`` and would FAIL on the unpatched ``boltz2-python-client``
0.5.1 release. They cover:

* Bug A — ``failed_requests`` is never reset on success, so a few transient
  failures permanently disable an endpoint.
* Bug B — ``_select_endpoint()`` ignores ``attempted_endpoints`` and so picks
  the same dead endpoint over and over inside a single dispatch loop.
* Bug C — ``health_check_sync()`` stores the ``HealthStatus`` object as a
  truthy boolean instead of normalising it, breaking the sync recovery path.
* Bug D — the background ``_health_check_loop`` waited a full
  ``health_check_interval`` before its first probe, so initial unreachability
  was invisible to the dispatcher.
* Bug E — ``__exit__`` crashed in synchronous use because it called
  ``asyncio.create_task`` without a running event loop.

All of these tests are pure unit tests (no live NIM required).
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from boltz2_client import (
    EndpointConfig,
    LoadBalanceStrategy,
    MultiEndpointClient,
)
from boltz2_client.exceptions import Boltz2APIError
from boltz2_client.models import (
    HealthStatus,
    PredictionRequest,
    PredictionResponse,
    Polymer,
    StructureData,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

OK_RESPONSE = PredictionResponse(
    structures=[StructureData(format="mmcif", structure="MOCK_CIF")],
    confidence_scores=[0.9],
)

DUMMY_REQUEST = PredictionRequest(
    polymers=[
        Polymer(
            id="A",
            molecule_type="protein",
            sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
        )
    ]
)


def _make_async_mec(num_endpoints: int = 3, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN):
    """Create a MultiEndpointClient with mocked async clients (no live calls).

    The background health-check task is cancelled so the tests are fully
    deterministic.
    """
    endpoints = [
        EndpointConfig(base_url=f"http://localhost:80{i:02d}") for i in range(num_endpoints)
    ]
    mec = MultiEndpointClient(
        endpoints=endpoints,
        strategy=strategy,
        is_async=True,
        health_check_interval=3600.0,
    )
    if mec._health_check_task is not None:
        mec._health_check_task.cancel()
        mec._health_check_task = None
    for ep in mec.endpoints:
        ep.client = Mock()
        ep.client.predict = AsyncMock()
        ep.client.health_check = AsyncMock()
    return mec


def _make_sync_mec(num_endpoints: int = 3):
    endpoints = [
        EndpointConfig(base_url=f"http://localhost:81{i:02d}") for i in range(num_endpoints)
    ]
    mec = MultiEndpointClient(
        endpoints=endpoints,
        strategy=LoadBalanceStrategy.ROUND_ROBIN,
        is_async=False,
        health_check_interval=3600.0,
    )
    for ep in mec.endpoints:
        ep.client = Mock()
        ep.client.predict = Mock()
        ep.client.health_check = Mock()
    return mec


# ---------------------------------------------------------------------------
# Bug A — failed_requests must reset on success
# ---------------------------------------------------------------------------


class TestBugAFailedRequestsResetOnSuccess:
    @pytest.mark.asyncio
    async def test_predict_resets_failed_requests_on_success(self):
        mec = _make_async_mec(num_endpoints=1)
        ep = mec.endpoints[0]

        # Simulate two earlier transient failures ...
        ep.failed_requests = 2
        ep.client.predict.return_value = OK_RESPONSE

        response = await mec.predict(DUMMY_REQUEST)

        assert response is OK_RESPONSE
        # ... that should now be cleared so the third failure does not push
        # the endpoint past the >=3 unhealthy threshold.
        assert ep.failed_requests == 0

    @pytest.mark.asyncio
    async def test_two_transient_failures_then_success_keeps_endpoint_healthy(self):
        mec = _make_async_mec(num_endpoints=1)
        ep = mec.endpoints[0]
        ep.client.predict.side_effect = [
            RuntimeError("transient 1"),
            RuntimeError("transient 2"),
        ]
        for _ in range(2):
            with pytest.raises(Boltz2APIError):
                await mec.predict(DUMMY_REQUEST)
        # Now succeed; this MUST reset failed_requests.
        ep.client.predict.side_effect = None
        ep.client.predict.return_value = OK_RESPONSE
        await mec.predict(DUMMY_REQUEST)
        assert ep.failed_requests == 0
        assert ep.is_healthy is True


# ---------------------------------------------------------------------------
# Bug B — _select_endpoint must not re-pick attempted endpoints
# ---------------------------------------------------------------------------


class TestBugBSelectEndpointHonorsAttempted:
    def test_select_endpoint_filters_attempted_set(self):
        mec = _make_async_mec(num_endpoints=3, strategy=LoadBalanceStrategy.LEAST_LOADED)
        first = mec._select_endpoint()
        attempted = {first.endpoint_config.base_url}
        second = mec._select_endpoint(attempted_endpoints=attempted)
        assert second is not first
        attempted.add(second.endpoint_config.base_url)
        third = mec._select_endpoint(attempted_endpoints=attempted)
        assert third.endpoint_config.base_url not in attempted
        attempted.add(third.endpoint_config.base_url)
        # Pool exhausted ⇒ None
        assert mec._select_endpoint(attempted_endpoints=attempted) is None

    def test_round_robin_skips_attempted_without_starvation(self):
        mec = _make_async_mec(num_endpoints=3, strategy=LoadBalanceStrategy.ROUND_ROBIN)
        # Pretend endpoint 0 was already tried within this request.
        attempted = {mec.endpoints[0].endpoint_config.base_url}
        chosen = mec._select_endpoint(attempted_endpoints=attempted)
        assert chosen is mec.endpoints[1]
        # Re-call with a fresh request — counter should have advanced past 0.
        nxt = mec._select_endpoint()
        # round-robin should now point at endpoint 2 (next in rotation)
        assert nxt is mec.endpoints[2]

    @pytest.mark.asyncio
    async def test_predict_does_not_loop_on_single_dead_endpoint(self):
        """The classic cascade: one endpoint fails repeatedly under
        LEAST_LOADED. Without the fix, _select_endpoint keeps re-picking it
        until the test times out.
        """
        mec = _make_async_mec(num_endpoints=2, strategy=LoadBalanceStrategy.LEAST_LOADED)
        bad, good = mec.endpoints
        bad.client.predict.side_effect = RuntimeError("bad")
        good.client.predict.return_value = OK_RESPONSE

        # If the bug is present, this hangs in an infinite loop and the
        # asyncio.wait_for guard fires.
        response = await asyncio.wait_for(mec.predict(DUMMY_REQUEST), timeout=2.0)
        assert response is OK_RESPONSE
        # The bad endpoint should have been tried exactly once.
        assert bad.client.predict.call_count == 1
        assert good.client.predict.call_count == 1


# ---------------------------------------------------------------------------
# Bug C — health_check_sync must normalise HealthStatus to bool
# ---------------------------------------------------------------------------


class TestBugCSyncHealthCheckNormalisation:
    def test_health_check_sync_stores_bool_not_object(self):
        mec = _make_sync_mec(num_endpoints=2)
        ts = datetime.now()
        for ep in mec.endpoints:
            ep.client.health_check.return_value = HealthStatus(status="healthy", timestamp=ts)

        agg = mec.health_check_sync()

        assert agg.status == "healthy"
        for ep in mec.endpoints:
            assert ep.is_healthy is True
            assert isinstance(ep.is_healthy, bool)

    def test_health_check_sync_marks_unhealthy_status(self):
        mec = _make_sync_mec(num_endpoints=1)
        mec.endpoints[0].client.health_check.return_value = HealthStatus(
            status="unhealthy", timestamp=datetime.now()
        )
        agg = mec.health_check_sync()
        assert agg.status == "unhealthy"
        assert mec.endpoints[0].is_healthy is False

    def test_health_check_sync_recovery_resets_failed_requests(self):
        mec = _make_sync_mec(num_endpoints=1)
        ep = mec.endpoints[0]
        ep.failed_requests = 5
        ep.is_healthy = False
        ep.client.health_check.return_value = HealthStatus(
            status="healthy", timestamp=datetime.now()
        )

        agg = mec.health_check_sync()
        assert agg.status == "healthy"
        assert ep.is_healthy is True
        assert ep.failed_requests == 0


# ---------------------------------------------------------------------------
# Bug D — background loop must prime an immediate health probe at startup
# ---------------------------------------------------------------------------


class TestBugDInitialHealthProbe:
    @pytest.mark.asyncio
    async def test_health_loop_probes_before_sleeping(self):
        """The first iteration must call _check_all_endpoints_health BEFORE
        the long sleep, otherwise startup unreachability is invisible until
        ``health_check_interval`` has elapsed.
        """
        endpoints = [EndpointConfig(base_url="http://localhost:8200")]
        mec = MultiEndpointClient(
            endpoints=endpoints,
            is_async=True,
            health_check_interval=10_000.0,  # would never trigger naturally
        )
        # Cancel auto-started loop so we control the ordering precisely.
        if mec._health_check_task is not None:
            mec._health_check_task.cancel()
            try:
                await mec._health_check_task
            except (asyncio.CancelledError, BaseException):
                pass

        called = asyncio.Event()

        async def fake_check():
            called.set()

        mec._check_all_endpoints_health = fake_check  # type: ignore[assignment]
        task = asyncio.create_task(mec._health_check_loop())
        try:
            # If the priming probe was missing, this would time out because
            # the loop would await asyncio.sleep(10_000) before calling.
            await asyncio.wait_for(called.wait(), timeout=1.0)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


# ---------------------------------------------------------------------------
# Bug E — sync context manager must not crash without a running loop
# ---------------------------------------------------------------------------


class TestBugESyncContextManager:
    def test_with_block_in_sync_code_does_not_raise(self):
        endpoints = [EndpointConfig(base_url="http://localhost:8300")]
        # ``with MultiEndpointClient(...)`` is a documented usage pattern; it
        # must not raise even when there is no running event loop.
        with MultiEndpointClient(
            endpoints=endpoints,
            is_async=False,
            health_check_interval=3600.0,
        ) as mec:
            assert mec is not None
            assert len(mec.endpoints) == 1

    def test_with_block_async_client_outside_loop_does_not_raise(self):
        """Even an ``is_async=True`` client constructed in a sync context
        must tolerate a context-manager exit without a running loop."""
        endpoints = [EndpointConfig(base_url="http://localhost:8301")]
        with MultiEndpointClient(
            endpoints=endpoints,
            is_async=True,
            health_check_interval=3600.0,
        ) as mec:
            assert mec is not None
