# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
A3M to CSV converter for Boltz-2 multimer predictions.

Converts ColabFold-generated A3M monomer MSA files into the paired CSV format
required by Boltz-2 for multimer structure predictions.

CSV Format for Boltz-2 Multimer:
    key,sequence
    1,SEQUENCE_A:SEQUENCE_B
    2,SEQUENCE_A':SEQUENCE_B'

Where SEQUENCE_A and SEQUENCE_B are paired sequences separated by ':'

Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
"""

import re
import logging
from typing import Dict, List, Optional, Set, Union
from pathlib import Path
from dataclasses import dataclass

from .parser import A3MParser, A3MMSA, A3MSequence
from .pairing import (
    PairingStrategy,
    GreedyPairingStrategy,
    CompletePairingStrategy,
    TaxonomyPairingStrategy,
)

logger = logging.getLogger(__name__)


@dataclass 
class ConversionResult:
    """Result of A3M to CSV conversion."""
    csv_content: str  # Combined CSV (for reference)
    csv_per_chain: Dict[str, str]  # Individual CSV per chain (for Boltz2 NIM)
    num_pairs: int
    chain_ids: List[str]
    query_sequences: Dict[str, str]
    output_path: Optional[Path] = None
    output_paths_per_chain: Optional[Dict[str, Path]] = None


class A3MToCSVConverter:
    """
    Converts multiple A3M monomer MSA files to paired CSV format for Boltz2 multimer predictions.
    
    Usage:
        converter = A3MToCSVConverter()
        
        # Convert from files
        result = converter.convert_files(
            a3m_files={
                'A': Path('chain_A.a3m'),
                'B': Path('chain_B.a3m')
            },
            output_path=Path('paired_msa.csv')
        )
        
        # Convert from content strings
        result = converter.convert_content(
            a3m_contents={
                'A': a3m_string_A,
                'B': a3m_string_B
            }
        )
    """
    
    def __init__(
        self,
        pairing_strategy: Optional[PairingStrategy] = None,
        include_unpaired: bool = False,
        max_pairs: Optional[int] = None
    ):
        """
        Initialize the converter.
        
        Args:
            pairing_strategy: Strategy for pairing sequences (default: GreedyPairingStrategy)
            include_unpaired: Whether to include unpaired sequences with gaps
            max_pairs: Maximum number of pairs to include (None = unlimited)
        """
        self.pairing_strategy = pairing_strategy or GreedyPairingStrategy()
        self.include_unpaired = include_unpaired
        self.max_pairs = max_pairs
    
    def convert_files(
        self,
        a3m_files: Dict[str, Path],
        output_path: Optional[Path] = None
    ) -> ConversionResult:
        """
        Convert multiple A3M files to paired CSV format.
        
        Args:
            a3m_files: Dictionary mapping chain IDs to A3M file paths
            output_path: Optional path to save the CSV file
            
        Returns:
            ConversionResult with CSV content and metadata
        """
        # Parse all A3M files
        msas = {}
        for chain_id, file_path in a3m_files.items():
            msa = A3MParser.parse_file(Path(file_path))
            msa.chain_id = chain_id
            msas[chain_id] = msa
            logger.info(f"Parsed chain {chain_id}: {len(msa.sequences)} sequences from {file_path}")
        
        return self._convert(msas, output_path)
    
    def convert_content(
        self,
        a3m_contents: Dict[str, str],
        output_path: Optional[Path] = None
    ) -> ConversionResult:
        """
        Convert multiple A3M content strings to paired CSV format.
        
        Args:
            a3m_contents: Dictionary mapping chain IDs to A3M content strings
            output_path: Optional path to save the CSV file
            
        Returns:
            ConversionResult with CSV content and metadata
        """
        # Parse all A3M content
        msas = {}
        for chain_id, content in a3m_contents.items():
            msa = A3MParser.parse(content)
            msa.chain_id = chain_id
            msas[chain_id] = msa
            logger.info(f"Parsed chain {chain_id}: {len(msa.sequences)} sequences")
        
        return self._convert(msas, output_path)
    
    # MSA size limits matching open-source Boltz-2 (src/boltz/data/const.py)
    MAX_PAIRED_SEQS = 8192
    MAX_MSA_SEQS = 16384

    def _convert(
        self,
        msas: Dict[str, A3MMSA],
        output_path: Optional[Path] = None
    ) -> ConversionResult:
        """
        Internal conversion logic.
        
        Creates both:
        1. A combined CSV with colon-separated sequences (for reference/documentation)
        2. Individual CSVs per chain with matching keys (for Boltz2 NIM API)
        
        Key conventions (matching open-source Boltz-2):
        - key=0: Query sequence (first row)
        - key=1..N: Paired sequences (same key across chains = co-evolved)
        - key=-1: Unpaired sequences (no pairing partner in other chains)
        
        When include_unpaired=True, also includes:
        - Unpaired sequences with key=-1 appended after paired sequences.
          Each unpaired sequence appears only in its own chain's CSV.
        
        MSA size limits (matching open-source Boltz-2):
        - Max paired sequences: 8192
        - Max total sequences: 16384
        
        Args:
            msas: Dictionary mapping chain IDs to parsed A3MMSA objects
            output_path: Optional path to save the combined CSV file
            
        Returns:
            ConversionResult with CSV content and metadata
        """
        chain_ids = sorted(msas.keys())
        
        # Find paired sequences
        pairs = self.pairing_strategy.find_pairs(msas)
        
        # Track which sequences have been paired (to find unpaired ones later)
        paired_sequence_ids: Dict[str, Set[str]] = {chain_id: set() for chain_id in chain_ids}
        for pair in pairs:
            for chain_id, seq in pair.items():
                paired_sequence_ids[chain_id].add(seq.identifier)
        
        # Apply MSA size limits (matching open-source Boltz-2 const.max_paired_seqs)
        max_paired = self.max_pairs if self.max_pairs else self.MAX_PAIRED_SEQS
        if len(pairs) > max_paired:
            logger.warning(f"Truncating paired sequences from {len(pairs)} to {max_paired} (max_paired_seqs limit)")
            pairs = pairs[:max_paired]
        
        logger.info(f"Found {len(pairs)} paired sequence sets across {len(chain_ids)} chains")
        
        # Extract query sequences and their lengths (for gap filling)
        query_sequences = {}
        query_lengths = {}
        for chain_id, msa in msas.items():
            query = msa.get_query()
            if query:
                clean_seq = self._clean_sequence(query.sequence)
                query_sequences[chain_id] = clean_seq
                query_lengths[chain_id] = len(clean_seq)
        
        # Separate query pair (key=0) from taxonomy-matched pairs (key=1..N)
        # The first pair from find_pairs() is the query pair
        query_pair = pairs[0] if pairs else {}
        taxonomy_pairs = pairs[1:] if len(pairs) > 1 else []
        
        # Collect unpaired sequences if requested, with deduplication
        unpaired_sequences: Dict[str, List[A3MSequence]] = {chain_id: [] for chain_id in chain_ids}
        num_unpaired = 0
        
        if self.include_unpaired:
            for chain_id, msa in msas.items():
                seen_seqs: Set[str] = set()  # Deduplicate by sequence content
                for seq in msa.sequences:
                    if seq.is_query:
                        continue
                    if seq.identifier not in paired_sequence_ids[chain_id]:
                        # Deduplicate by cleaned sequence content (matching open-source behavior)
                        clean = self._clean_sequence(seq.sequence).replace('-', '').upper()
                        if clean not in seen_seqs:
                            seen_seqs.add(clean)
                            unpaired_sequences[chain_id].append(seq)
                            num_unpaired += 1
            
            # Apply MSA size limit: unpaired capped at (max_msa_seqs - num_paired)
            max_unpaired = self.MAX_MSA_SEQS - len(pairs)
            if num_unpaired > max_unpaired:
                logger.warning(f"Truncating unpaired sequences from {num_unpaired} to {max_unpaired} (max_msa_seqs limit)")
                # Distribute cap proportionally across chains
                remaining = max_unpaired
                for chain_id in chain_ids:
                    chain_limit = max(1, remaining // max(1, len(chain_ids)))
                    unpaired_sequences[chain_id] = unpaired_sequences[chain_id][:chain_limit]
                    remaining -= len(unpaired_sequences[chain_id])
                num_unpaired = sum(len(v) for v in unpaired_sequences.values())
            
            logger.info(f"Found {num_unpaired} unpaired sequences (key=-1)")
        
        # Build per-chain CSVs (for Boltz2 NIM API)
        # Key convention: 0=query, 1..N=paired, -1=unpaired
        csv_per_chain: Dict[str, str] = {}
        for chain_id in chain_ids:
            chain_lines = ["key,sequence"]
            
            # Key 0: Query sequence
            if chain_id in query_pair:
                seq = self._clean_sequence(query_pair[chain_id].sequence)
                chain_lines.append(f"0,{seq}")
            
            # Keys 1..N: Paired sequences (taxonomy-matched)
            for idx, pair in enumerate(taxonomy_pairs, start=1):
                if chain_id in pair:
                    seq = self._clean_sequence(pair[chain_id].sequence)
                    chain_lines.append(f"{idx},{seq}")
                else:
                    # Use gaps if sequence not found for this chain (greedy partial match)
                    gap_seq = '-' * query_lengths.get(chain_id, 0)
                    chain_lines.append(f"{idx},{gap_seq}")
            
            csv_per_chain[chain_id] = '\n'.join(chain_lines)
        
        # Add unpaired sequences with key=-1 (matching open-source Boltz-2)
        if self.include_unpaired:
            for chain_id in chain_ids:
                for unpaired_seq in unpaired_sequences[chain_id]:
                    seq = self._clean_sequence(unpaired_seq.sequence)
                    csv_per_chain[chain_id] += f"\n-1,{seq}"
        
        # Build combined CSV (for reference/documentation)
        csv_lines = ["key,sequence"]
        
        # Key 0: Query
        if query_pair:
            sequences = []
            for chain_id in chain_ids:
                if chain_id in query_pair:
                    seq = self._clean_sequence(query_pair[chain_id].sequence)
                    sequences.append(seq)
                else:
                    sequences.append('-' * query_lengths.get(chain_id, 0))
            csv_lines.append(f"0,{':'.join(sequences)}")
        
        # Keys 1..N: Paired
        for idx, pair in enumerate(taxonomy_pairs, start=1):
            sequences = []
            for chain_id in chain_ids:
                if chain_id in pair:
                    seq = self._clean_sequence(pair[chain_id].sequence)
                    sequences.append(seq)
                else:
                    sequences.append('-' * query_lengths.get(chain_id, 0))
            csv_lines.append(f"{idx},{':'.join(sequences)}")
        
        # Key -1: Unpaired (combined CSV shows which chain each comes from)
        if self.include_unpaired:
            for source_chain_id in chain_ids:
                for unpaired_seq in unpaired_sequences[source_chain_id]:
                    sequences = []
                    for chain_id in chain_ids:
                        if chain_id == source_chain_id:
                            seq = self._clean_sequence(unpaired_seq.sequence)
                            sequences.append(seq)
                        else:
                            sequences.append('-' * query_lengths.get(chain_id, 0))
                    csv_lines.append(f"-1,{':'.join(sequences)}")
        
        csv_content = '\n'.join(csv_lines)
        
        total_rows = len(pairs) + (num_unpaired if self.include_unpaired else 0)
        logger.info(f"Total MSA rows: {total_rows} ({len(pairs)} paired + {num_unpaired if self.include_unpaired else 0} unpaired)")
        
        # Save files if path provided
        output_paths_per_chain = None
        if output_path:
            output_path = Path(output_path)
            # Save combined CSV
            output_path.write_text(csv_content)
            logger.info(f"Saved combined paired MSA CSV to {output_path}")
            
            # Save per-chain CSVs
            output_paths_per_chain = {}
            for chain_id, chain_csv in csv_per_chain.items():
                chain_path = output_path.parent / f"{output_path.stem}_chain_{chain_id}.csv"
                chain_path.write_text(chain_csv)
                output_paths_per_chain[chain_id] = chain_path
                logger.info(f"Saved chain {chain_id} CSV to {chain_path}")
        
        return ConversionResult(
            csv_content=csv_content,
            csv_per_chain=csv_per_chain,
            num_pairs=len(pairs),
            chain_ids=chain_ids,
            query_sequences=query_sequences,
            output_path=output_path,
            output_paths_per_chain=output_paths_per_chain
        )
    
    @staticmethod
    def _clean_sequence(sequence: str) -> str:
        """
        Clean sequence for CSV output.
        
        Removes lowercase characters (insertions in A3M format) 
        to get the aligned sequence.
        
        Args:
            sequence: Raw sequence from A3M
            
        Returns:
            Cleaned sequence with only uppercase letters and gaps
        """
        # A3M format uses lowercase for insertions - remove them
        # Keep uppercase letters and gaps (-)
        return re.sub(r'[a-z]', '', sequence)


def _auto_detect_tax_id_mode(a3m_files: Dict[str, Path]) -> bool:
    """
    Auto-detect whether to use TaxID or UniRef ID pairing based on A3M file contents.
    
    This implements ColabFold's default behavior:
    - If TaxIDs are present in the MSA headers (via OX= field, species codes, etc.),
      use TaxID-based pairing for biologically meaningful co-evolution signals
    - If no TaxIDs are found (standard ColabFold UniRef100 output), fall back to
      UniRef cluster ID pairing
    
    Args:
        a3m_files: Dictionary mapping chain IDs to A3M file paths
        
    Returns:
        True if TaxIDs should be used for pairing, False otherwise
    """
    total_sequences = 0
    sequences_with_tax_id = 0
    
    for chain_id, a3m_path in a3m_files.items():
        try:
            if isinstance(a3m_path, str):
                a3m_path = Path(a3m_path)
            
            msa = A3MParser.parse_file(a3m_path)
            
            for seq in msa.sequences:
                if seq.is_query:
                    continue
                total_sequences += 1
                # Check if this sequence has a valid TaxID (numeric)
                if seq.tax_id and seq.tax_id.isdigit():
                    sequences_with_tax_id += 1
                    
        except Exception as e:
            logger.warning(f"Error parsing {a3m_path} for auto-detection: {e}")
            continue
    
    if total_sequences == 0:
        logger.info("No sequences found for auto-detection, defaulting to UniRef ID pairing")
        return False
    
    # If more than 50% of sequences have TaxIDs, use TaxID pairing
    tax_id_ratio = sequences_with_tax_id / total_sequences
    use_tax_id = tax_id_ratio > 0.5
    
    logger.debug(
        f"Auto-detect: {sequences_with_tax_id}/{total_sequences} sequences "
        f"({tax_id_ratio:.1%}) have TaxIDs. Using {'TaxID' if use_tax_id else 'UniRef ID'} pairing."
    )
    
    return use_tax_id


def convert_a3m_to_multimer_csv(
    a3m_files: Dict[str, Path],
    output_path: Optional[Path] = None,
    pairing_strategy: str = "greedy",
    use_tax_id: Optional[bool] = None,  # None = auto-detect (ColabFold default)
    include_unpaired: bool = False,
    max_pairs: Optional[int] = None
) -> ConversionResult:
    """
    Convenience function to convert A3M files to multimer CSV format.
    
    This function implements ColabFold-style MSA pairing for Boltz2 multimer predictions.
    
    Args:
        a3m_files: Dictionary mapping chain IDs (e.g., 'A', 'B') to A3M file paths
        output_path: Optional path to save the CSV file
        pairing_strategy: Pairing strategy - 'greedy' (default, like ColabFold) or 'complete'
            - 'greedy': Pairs any subset of chains with matching identifier (ColabFold default)
            - 'complete': Only pairs if ALL chains have matching identifier
        use_tax_id: Pairing identifier mode (ColabFold-style auto-detection by default):
            - None (default): Auto-detect. Use TaxID if available in headers, 
                             otherwise fall back to UniRef cluster ID pairing.
                             This is how ColabFold behaves.
            - True: Force TaxID pairing (requires OX= or species codes in headers)
            - False: Force UniRef/organism ID pairing (works with standard ColabFold output)
        include_unpaired: If True, include sequences without cross-chain matches in 
                         "block-diagonal" format (one chain has sequence, others have gaps).
                         This maximizes MSA depth while still providing pairing where available.
                         Default: False (only paired sequences are included)
        max_pairs: Maximum number of pairs to include
        
    Returns:
        ConversionResult with CSV content and metadata
        
    Example:
        >>> # ColabFold-style pairing (auto-detect, recommended)
        >>> result = convert_a3m_to_multimer_csv(
        ...     a3m_files={'A': Path('chain_A.a3m'), 'B': Path('chain_B.a3m')},
        ...     output_path=Path('paired.csv'),
        ...     pairing_strategy='greedy',  # Like ColabFold
        ...     # use_tax_id=None means auto-detect (default)
        ... )
        >>> print(f"Created {result.num_pairs} paired sequences")
        
        >>> # Include unpaired sequences for maximum MSA depth
        >>> result = convert_a3m_to_multimer_csv(
        ...     a3m_files={'A': Path('chain_A.a3m'), 'B': Path('chain_B.a3m')},
        ...     include_unpaired=True  # Block-diagonal format
        ... )
    
    ColabFold Compatibility:
        Standard ColabFold A3M files use UniRef100 cluster IDs without TaxID information.
        With use_tax_id=None (default), the converter will:
        1. Parse all A3M files and check for TaxID presence
        2. If TaxIDs found (OX= fields, species codes like _HUMAN), use TaxID pairing
        3. If no TaxIDs found, fall back to UniRef cluster ID pairing
        
        This matches ColabFold's behavior where taxonomy-based pairing is preferred
        but the system gracefully handles files without taxonomy annotations.
    """
    # Auto-detect TaxID availability if use_tax_id is None
    if use_tax_id is None:
        use_tax_id = _auto_detect_tax_id_mode(a3m_files)
        logger.info(f"Auto-detected pairing mode: {'TaxID' if use_tax_id else 'UniRef ID'}")
    
    strategy: PairingStrategy
    if pairing_strategy == "greedy":
        strategy = GreedyPairingStrategy(use_tax_id=use_tax_id)
    elif pairing_strategy == "complete":
        strategy = CompletePairingStrategy(use_tax_id=use_tax_id)
    elif pairing_strategy == "taxonomy":
        # Alias for greedy + use_tax_id=True
        strategy = TaxonomyPairingStrategy(strategy="greedy")
    else:
        raise ValueError(f"Unknown pairing strategy: {pairing_strategy}. Use 'greedy', 'complete', or 'taxonomy'")
    
    converter = A3MToCSVConverter(
        pairing_strategy=strategy,
        include_unpaired=include_unpaired,
        max_pairs=max_pairs
    )
    
    return converter.convert_files(a3m_files, output_path)


def create_multimer_msa_request(
    chain_sequences: Dict[str, str],
    csv_content: str
) -> Dict[str, Dict[str, Dict]]:
    """
    Create MSA data structure for Boltz2 multimer prediction request.
    
    DEPRECATED: Use create_paired_msa_per_chain() instead for Boltz2 NIM API.
    
    Args:
        chain_sequences: Dictionary mapping chain IDs to query sequences
        csv_content: Paired MSA in CSV format (combined)
        
    Returns:
        MSA data structure in Boltz2 format
    """
    from ..models import AlignmentFileRecord
    
    msa_record = AlignmentFileRecord(
        alignment=csv_content,
        format="csv",
        rank=0
    )
    
    return {"paired": {"csv": msa_record}}


def create_paired_msa_per_chain(
    conversion_result: ConversionResult
) -> Dict[str, Dict[str, Dict]]:
    """
    Create per-chain MSA data structures for Boltz2 NIM API.
    
    The Boltz2 NIM API requires each polymer to have its own MSA where:
    - Each chain gets a CSV with columns: key, sequence
    - Rows with matching 'key' values across chains are paired
    - This enables proper co-evolutionary signal for multimer prediction
    
    Args:
        conversion_result: Result from A3MToCSVConverter
        
    Returns:
        Dictionary mapping chain IDs to MSA data structures
        
    Example:
        >>> result = convert_a3m_to_multimer_csv(
        ...     a3m_files={'A': Path('chain_A.a3m'), 'B': Path('chain_B.a3m')}
        ... )
        >>> msa_per_chain = create_paired_msa_per_chain(result)
        >>> 
        >>> protein_A = Polymer(id='A', sequence='...', msa=msa_per_chain['A'])
        >>> protein_B = Polymer(id='B', sequence='...', msa=msa_per_chain['B'])
    """
    from ..models import AlignmentFileRecord
    
    msa_per_chain = {}
    for chain_id, csv_content in conversion_result.csv_per_chain.items():
        msa_record = AlignmentFileRecord(
            alignment=csv_content,
            format="csv",
            rank=0
        )
        msa_per_chain[chain_id] = {"paired": {"csv": msa_record}}
    
    return msa_per_chain

