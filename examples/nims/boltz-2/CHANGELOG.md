# Changelog

All notable changes to this project will be documented in this file.

## [0.5.2] - 2026-02-24

### Fixed — `MultiEndpointClient` reliability
- **No longer cascades into "All endpoints failed" after a single endpoint glitch.**
  `failed_requests` is now reset on every successful call across all
  `predict_*` methods (`predict`, `predict_sync`, `predict_protein_structure`,
  `predict_protein_ligand_complex`, `predict_covalent_complex`,
  `predict_dna_protein_complex`, `predict_with_advanced_parameters`,
  `predict_from_yaml_config`, `predict_from_yaml_file`, and the
  corresponding `*_sync` variants). Previously a recovered endpoint could
  remain marked unhealthy indefinitely after three transient failures.
- **`_select_endpoint()` now honours the per-request `attempted_endpoints`
  set.** The `LEAST_LOADED` and `RANDOM` strategies could otherwise re-pick
  the same dead endpoint repeatedly inside a single dispatch loop, wasting
  retries and (on `LEAST_LOADED`) starving healthy endpoints. Round-robin
  also now skips already-attempted endpoints fairly without resetting the
  global rotation counter.
- **`health_check_sync()` now normalises `HealthStatus` to a boolean.**
  Previously it stored the entire `HealthStatus` object on
  `EndpointStatus.is_healthy`, which is always truthy and broke the sync
  recovery + status-table paths.
- **Background health-check loop runs an immediate probe at startup.**
  Initial unreachability is now detected without waiting a full
  `health_check_interval` (default 60 s).
- **Synchronous `__exit__` no longer crashes when no event loop is running.**
  `with MultiEndpointClient(...)` is now safe in plain synchronous code.

### Fixed — CLI
- `boltz2 msa-search`, `boltz2 msa-predict`, and `boltz2 msa-ligand` now
  exit with a non-zero status when the underlying call fails (previously
  they printed the error and exited cleanly, masking failures in pipelines).
- `boltz2 screen` now reports a clear error if client initialization fails
  or if `--pocket-residues` is malformed, instead of crashing with a stack
  trace before the progress UI starts.
- Removed a redundant local `import json` inside
  `boltz2 multimer-msa --save-all`; the module-level import is used.

### Fixed — virtual screening
- `VirtualScreening` no longer raises `IndexError` when a prediction
  response comes back with empty `structures`, `confidence_scores`, or
  affinity score lists; missing fields are reported as `None` and the
  campaign continues.

### Fixed — async client
- `Boltz2Client._sagemaker_predict` now uses `asyncio.get_running_loop()`
  instead of the deprecated `asyncio.get_event_loop()` (silences the
  Python 3.10+ `DeprecationWarning` and avoids a future-version hard
  error).

### Added
- **`boltz2 --version` / `boltz2 -V`** prints the installed package
  version (previously the CLI had no version flag).

### Removed
- Dead `_HAS_VISUALIZATION` / `_HAS_ANALYSIS` optional-import scaffolding
  in `boltz2_client/__init__.py` referencing modules that have never
  shipped. The package public surface is unchanged: no name was ever
  successfully exported from those blocks.

### Docs
- Updated the README tagline to accurately describe what ships in the
  package (multi-endpoint load balancing + notebook examples that
  visualize structures with `py3Dmol` and Molstar) instead of claiming a
  non-existent "built-in 3D visualization" module.

### Tests
- Added `tests/test_multi_endpoint_reliability.py` with 11 regression
  tests pinning each of the fixes above. Each test fails on 0.5.1 and
  passes on 0.5.2; the full suite (excluding live-endpoint tests) is now
  134 passing.

## [0.5.1] - 2026-04-07

### Fixed
- CLI `metadata` command now shows a clear error for SageMaker endpoints instead of a cryptic `NoneType` error
- SageMaker endpoint exception handling cleanup in CLI

## [0.5.0] - 2026-04-07

### Added
- AWS SageMaker endpoint support (`EndpointType.SAGEMAKER`, CLI `--endpoint-type sagemaker`, `--sagemaker-endpoint-name`, `--sagemaker-region`)

### Changed
- **PocketConstraint API** now uses `Contact` objects (binder + contacts)
- **Parameter ranges:** `recycling_steps` 1–10, `diffusion_samples` 1–25
- **`write_full_pde`** support for full predicted distance error matrix output
- **`Ligand.id`** is optional
- Compatibility updates for **Boltz-2 NIM v1.6.0**

### Fixed
- Comprehensive test suite fixes and live endpoint tests

## [0.4.0] - 2025-11-01

### Added
- A3M to multimer MSA conversion utilities, `multimer-msa` and `convert-msa` CLI commands
- Example script `13_a3m_to_multimer_csv.py` and guides (`docs/a3m_to_multimer_msa.md`)
- Multimer notebooks (`01_multimer_prediction.ipynb`, `03_colabfold_a3m_to_multimer.ipynb`) and related example scripts
- `08_affinity_prediction_simple.py` as the maintained affinity example (with `kinase_y7w_affinity.json`)

### Changed
- Multi-endpoint client default load-balancing strategy documented as **least-loaded**; expanded multi-endpoint coverage across prediction APIs
- README and guides updated for v1.5 NIM parameter limits (recycling/diffusion), PAE/PDE output, and PDB export

### Documentation
- Multi-endpoint virtual screening guide and examples (`comprehensive_multi_endpoint_demo.py`, `multi_endpoint_screening.py`)

## [0.3.0] - 2025-09-11

### Added
- **GPU-accelerated MSA Search NIM Integration**:
  - New `MSASearchClient` for direct MSA Search NIM interaction
  - `MSAFormatConverter` for A3M, FASTA, and Stockholm format support
  - `MSASearchIntegration` for Boltz-2 workflow integration
- **New Client Methods**:
  - `configure_msa_search()` - Configure MSA Search NIM endpoint
  - `search_msa()` - Standalone MSA search
  - `predict_with_msa_search()` - Integrated MSA + structure prediction
  - `predict_ligand_with_msa_search()` - MSA + ligand + affinity prediction
  - `batch_msa_search()` - Batch processing for multiple sequences
- **CLI Commands**:
  - `boltz2 msa-search` - Search and save MSA alignments
  - `boltz2 msa-predict` - Combined MSA search + structure prediction
  - `boltz2 msa-ligand` - MSA-guided ligand affinity prediction
  - `--msa-file` option for existing MSA files
- **Examples**:
  - `10_msa_search_integration.py` - Comprehensive MSA integration demo
  - `11_msa_search_large_protein.py` - Large protein optimization
  - `12_msa_affinity_prediction.py` - MSA-guided affinity prediction
- **Documentation**:
  - New MSA Search Guide with complete usage examples
  - Updated Affinity Prediction Guide with MSA-guided section
  - Enhanced README with MSA integration examples

### Fixed
- Parameter naming consistency: `max_hits` → `max_msa_sequences`, `e_value_threshold` → `e_value`
- MSA file handling in `predict_protein_structure()` method
- Documentation inconsistencies and outdated examples

### Improved
- Better error handling for MSA Search API responses
- Retry logic for MSA Search requests
- More comprehensive test coverage

## [0.2.1] - 2025-08-14

### Added
- Complete multi-endpoint support for ALL Boltz2 NIM functionalities:
  - `predict_protein_structure()` with MSA support
  - `predict_protein_ligand_complex()` with affinity prediction
  - `predict_covalent_complex()`
  - `predict_dna_protein_complex()`
  - `predict_with_advanced_parameters()`
  - `predict_from_yaml_config()` and `predict_from_yaml_file()`
- New `msa` parameter in `predict_protein_structure()` for direct MSA input
- Comprehensive demo notebook (`examples/boltz2_comprehensive_demo.ipynb`) with:
  - Single and multi-endpoint examples
  - Both Python API and CLI demonstrations
  - Advanced features and visualization
- `AlignmentFormat` export in `__init__.py`

### Fixed
- MSA support now correctly uses nested dictionary format `{database: {format: AlignmentFileRecord}}`
- CLI multi-endpoint initialization (removed incorrect `is_async` parameter)
- Multi-endpoint client MSA parameter passing
- YAML configuration MSA format handling

### Changed
- Updated README.md examples (removed `is_async=True` from MultiEndpointClient)
- Improved error handling in multi-endpoint operations
- Better organization of test scripts into `test_scripts/` directory

### Documentation
- New comprehensive demo notebook with complete examples
- Updated all guides for consistency
- Added troubleshooting tips for multi-endpoint usage

## [0.2.0] - Previous release
- Initial multi-endpoint support for virtual screening
- Basic affinity prediction features
- Virtual screening capabilities
