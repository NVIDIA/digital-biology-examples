# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
MSA pairing strategies for multimer sequence alignment.

Provides greedy, complete, and taxonomy-based pairing strategies that
match sequences across chains by taxonomic ID or organism identifier.

Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
"""

import logging
from typing import Dict, List, Set
from collections import defaultdict

from .parser import A3MMSA, A3MSequence

logger = logging.getLogger(__name__)


class PairingStrategy:
    """Base class for MSA pairing strategies."""
    
    def find_pairs(
        self, 
        msas: Dict[str, A3MMSA]
    ) -> List[Dict[str, A3MSequence]]:
        """
        Find paired sequences across MSAs.
        
        Args:
            msas: Dictionary mapping chain ID to A3MMSA
            
        Returns:
            List of dictionaries mapping chain ID to paired sequence
        """
        raise NotImplementedError


class GreedyPairingStrategy(PairingStrategy):
    """
    Greedy pairing strategy based on taxonomic ID matching (like ColabFold).
    
    This is the default strategy used by ColabFold (since June 2023) and Boltz2.
    
    Key behavior:
    - Pairs sequences from the same taxonomic ID (species) across chains
    - "Greedy" means it pairs ANY subset of chains that have matching TaxID
    - If only 2 out of 3 chains have a TaxID match, those 2 are still paired
    - Uses the UNION of TaxIDs across all pairwise chain comparisons
    
    This differs from "complete" pairing which requires ALL chains to match.
    """
    
    def __init__(self, use_tax_id: bool = True):
        """
        Initialize greedy pairing strategy.
        
        Args:
            use_tax_id: If True, use taxonomic IDs for pairing (like ColabFold).
                       If False, fall back to organism_id/UniRef cluster matching.
        """
        self.use_tax_id = use_tax_id
    
    def find_pairs(
        self, 
        msas: Dict[str, A3MMSA]
    ) -> List[Dict[str, A3MSequence]]:
        """
        Find paired sequences using greedy matching on taxonomic IDs.
        
        Greedy pairing collects all TaxIDs that appear in at least 2 chains,
        then for each such TaxID, creates a partial pair with whichever chains
        have that TaxID. This matches ColabFold's pairgreedy behavior.
        
        Args:
            msas: Dictionary mapping chain ID to A3MMSA
            
        Returns:
            List of dictionaries mapping chain ID to paired sequence
        """
        if not msas:
            return []
        
        chain_ids = list(msas.keys())
        pairs = []
        
        # First, add the query sequences as pair with key 0
        query_pair = {}
        for chain_id, msa in msas.items():
            query = msa.get_query()
            if query:
                query_pair[chain_id] = query
        
        if len(query_pair) == len(chain_ids):
            pairs.append(query_pair)
        
        # Get all unique IDs (TaxID or organism_id based on setting)
        if self.use_tax_id:
            id_sets = {cid: msa.get_tax_ids() for cid, msa in msas.items()}
            get_seq_func = lambda msa, id_val: msa.get_sequence_by_tax_id(id_val)
            id_type = "TaxID"
        else:
            id_sets = {cid: msa.get_organism_ids() for cid, msa in msas.items()}
            get_seq_func = lambda msa, id_val: msa.get_sequence_by_id(id_val)
            id_type = "organism ID"
        
        if not id_sets or not any(id_sets.values()):
            return pairs
        
        # Greedy: collect TaxIDs that appear in at least 2 chains (union of
        # pairwise intersections), then build partial pairs for each.
        # Count how many chains each TaxID appears in.
        tax_id_chain_count: Dict[str, int] = defaultdict(int)
        for cid, ids in id_sets.items():
            for tid in ids:
                tax_id_chain_count[tid] += 1
        
        # Keep TaxIDs present in >=2 chains (greedy allows partial matches)
        candidate_ids = sorted(tid for tid, cnt in tax_id_chain_count.items() if cnt >= 2)
        
        logger.info(f"Found {len(candidate_ids)} {id_type}s present in >=2 chains (greedy) across {len(chain_ids)} chains")
        
        # Create pairs for each candidate ID
        for tax_id in candidate_ids:
            pair = {}
            for chain_id, msa in msas.items():
                seq = get_seq_func(msa, tax_id)
                if seq:
                    pair[chain_id] = seq
            
            # Greedy: include if at least 2 chains matched
            if len(pair) >= 2:
                pairs.append(pair)
        
        return pairs


class CompletePairingStrategy(PairingStrategy):
    """
    Complete pairing strategy (like ColabFold's original behavior).
    
    This was ColabFold's default before June 2023.
    
    Key behavior:
    - Only creates a pair if ALL chains have matching taxonomic ID
    - Uses intersection of TaxID sets across all chains
    - More strict than greedy, results in fewer pairs
    - Use when you want high-confidence complete pairings only
    """
    
    def __init__(self, use_tax_id: bool = True):
        """
        Initialize complete pairing strategy.
        
        Args:
            use_tax_id: If True, use taxonomic IDs for pairing.
        """
        self.use_tax_id = use_tax_id
    
    def find_pairs(
        self, 
        msas: Dict[str, A3MMSA]
    ) -> List[Dict[str, A3MSequence]]:
        """
        Find paired sequences requiring ALL chains to have matching TaxID.
        
        Complete pairing uses the intersection of TaxID sets across all chains,
        then only includes pairs where every chain has a matching sequence.
        This differs from greedy for 3+ chains where greedy allows partial matches.
        
        Args:
            msas: Dictionary mapping chain ID to A3MMSA
            
        Returns:
            List of dictionaries mapping chain ID to paired sequence
        """
        if not msas:
            return []
        
        chain_ids = list(msas.keys())
        pairs = []
        
        # First, add the query sequences as pair with key 0
        query_pair = {}
        for chain_id, msa in msas.items():
            query = msa.get_query()
            if query:
                query_pair[chain_id] = query
        
        if len(query_pair) == len(chain_ids):
            pairs.append(query_pair)
        
        # Get all unique IDs (TaxID or organism_id based on setting)
        if self.use_tax_id:
            id_sets = [msa.get_tax_ids() for msa in msas.values()]
            get_seq_func = lambda msa, id_val: msa.get_sequence_by_tax_id(id_val)
            id_type = "TaxID"
        else:
            id_sets = [msa.get_organism_ids() for msa in msas.values()]
            get_seq_func = lambda msa, id_val: msa.get_sequence_by_id(id_val)
            id_type = "organism ID"
        
        if not id_sets or not any(id_sets):
            return pairs
        
        # Complete: use strict intersection across ALL chains
        common_ids = id_sets[0].copy()
        for id_set in id_sets[1:]:
            common_ids &= id_set
        
        logger.info(f"Found {len(common_ids)} common {id_type}s across ALL {len(chain_ids)} chains (complete)")
        
        # Create pairs only where ALL chains have a matching sequence
        for tax_id in sorted(common_ids):
            pair = {}
            for chain_id, msa in msas.items():
                seq = get_seq_func(msa, tax_id)
                if seq:
                    pair[chain_id] = seq
            
            # Complete: require ALL chains to have this ID
            if len(pair) == len(chain_ids):
                pairs.append(pair)
        
        return pairs


class TaxonomyPairingStrategy(PairingStrategy):
    """
    Taxonomy-based pairing strategy using NCBI Taxonomic IDs.
    
    This is the strategy that most closely matches ColabFold's behavior:
    - Uses NCBI TaxID (e.g., 9606 for human, 10090 for mouse)
    - Extracted from OX= field, species codes, or header annotations
    - Sequences with same TaxID are considered from same species → paired
    
    This is now the RECOMMENDED strategy for ColabFold-style pairing.
    """
    
    def __init__(self, strategy: str = "greedy"):
        """
        Initialize taxonomy pairing strategy.
        
        Args:
            strategy: "greedy" (default since ColabFold June 2023) or "complete"
        """
        self.strategy = strategy
    
    def find_pairs(
        self, 
        msas: Dict[str, A3MMSA]
    ) -> List[Dict[str, A3MSequence]]:
        """
        Find paired sequences using taxonomic ID matching (like ColabFold).
        
        Args:
            msas: Dictionary mapping chain ID to A3MMSA
            
        Returns:
            List of dictionaries mapping chain ID to paired sequence
        """
        if self.strategy == "greedy":
            impl = GreedyPairingStrategy(use_tax_id=True)
        else:
            impl = CompletePairingStrategy(use_tax_id=True)
        
        return impl.find_pairs(msas)

