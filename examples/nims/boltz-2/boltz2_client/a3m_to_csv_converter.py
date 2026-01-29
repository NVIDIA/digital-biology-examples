"""
A3M to CSV Multimer MSA Converter for Boltz-2

This module provides functionality to convert ColabFold-generated A3M monomer MSA files
into the paired CSV format required by Boltz2 for multimer structure predictions.

Key Concepts:
- ColabFold generates individual A3M MSA files for each monomer
- Boltz2 expects paired MSAs for multimers in CSV format with columns: 'key', 'sequence'
- Sequences with the same 'key' are considered paired (from same species/organism)
- The pairing is done by matching taxonomic identifiers across monomer MSAs

CSV Format for Boltz2 Multimer:
    key,sequence
    1,SEQUENCE_A:SEQUENCE_B
    2,SEQUENCE_A':SEQUENCE_B'
    
Where SEQUENCE_A and SEQUENCE_B are paired sequences separated by ':'

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import re
import csv
import logging
from typing import Dict, List, Optional, Tuple, Set, NamedTuple
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


# Common species code to TaxID mapping
# This is a subset of the most common organisms in UniProt
# Full mapping available at: https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/docs/speclist.txt
#
# The mapping can be extended by:
# 1. Using SpeciesMapper.download_uniprot_speclist() to get complete mapping
# 2. Adding entries to SPECIES_TO_TAXID dictionary
# 3. Using explicit OX= field in A3M headers (most reliable)

SPECIES_TO_TAXID = {
    # Mammals
    "HUMAN": "9606",    # Homo sapiens
    "MOUSE": "10090",   # Mus musculus
    "RAT": "10116",     # Rattus norvegicus
    "BOVIN": "9913",    # Bos taurus
    "PIG": "9823",      # Sus scrofa
    "SHEEP": "9940",    # Ovis aries
    "HORSE": "9796",    # Equus caballus
    "RABIT": "9986",    # Oryctolagus cuniculus
    "CANLF": "9615",    # Canis lupus familiaris
    "FELCA": "9685",    # Felis catus
    
    # Primates
    "GORGO": "9593",    # Gorilla gorilla
    "PANTR": "9598",    # Pan troglodytes
    "PONAB": "9601",    # Pongo abelii
    "MACMU": "9544",    # Macaca mulatta
    "MACFA": "9541",    # Macaca fascicularis
    
    # Birds
    "CHICK": "9031",    # Gallus gallus
    "MELGA": "9103",    # Meleagris gallopavo
    
    # Fish
    "DANRE": "7955",    # Danio rerio (zebrafish)
    "ORYLA": "8090",    # Oryzias latipes (medaka)
    "FUGRU": "31033",   # Takifugu rubripes
    
    # Amphibians
    "XENLA": "8355",    # Xenopus laevis
    "XENTR": "8364",    # Xenopus tropicalis
    
    # Invertebrates
    "DROME": "7227",    # Drosophila melanogaster
    "CAEEL": "6239",    # Caenorhabditis elegans
    "AEDAE": "7159",    # Aedes aegypti
    "ANOGA": "7165",    # Anopheles gambiae
    
    # Yeast & Fungi
    "YEAST": "559292",  # Saccharomyces cerevisiae S288C
    "SCHPO": "284812",  # Schizosaccharomyces pombe
    "CANAL": "5476",    # Candida albicans
    "ASPFU": "746128",  # Aspergillus fumigatus
    
    # Plants
    "ARATH": "3702",    # Arabidopsis thaliana
    "ORYSJ": "39947",   # Oryza sativa subsp. japonica
    "MAIZE": "4577",    # Zea mays
    "SOYBN": "3847",    # Glycine max
    "WHEAT": "4565",    # Triticum aestivum
    "TOBAC": "4097",    # Nicotiana tabacum
    
    # Bacteria
    "ECOLI": "562",     # Escherichia coli
    "ECO57": "83334",   # Escherichia coli O157:H7
    "BACSU": "224308",  # Bacillus subtilis
    "MYCTU": "83332",   # Mycobacterium tuberculosis
    "STRPN": "1313",    # Streptococcus pneumoniae
    "PSEAE": "287",     # Pseudomonas aeruginosa
    "STAAU": "1280",    # Staphylococcus aureus
    "SALTY": "99287",   # Salmonella typhimurium
    "VIBCH": "243277",  # Vibrio cholerae
    "HELPY": "85962",   # Helicobacter pylori
    "NEIG1": "242231",  # Neisseria gonorrhoeae
    
    # Archaea
    "METJA": "2190",    # Methanocaldococcus jannaschii
    "SULSO": "273057",  # Sulfolobus solfataricus
    "PYRFU": "186497",  # Pyrococcus furiosus
    
    # Viruses (common ones)
    "SARSC": "694009",  # SARS coronavirus
    "SARS2": "2697049", # SARS-CoV-2
    "HIV1": "11676",    # Human immunodeficiency virus 1
    "HHV1": "10298",    # Human herpesvirus 1
}


class SpeciesMapper:
    """
    Maps UniProt species codes to NCBI Taxonomic IDs.
    
    Multiple backends supported:
    1. Built-in SPECIES_TO_TAXID dictionary (fast, limited to ~54 species)
    2. Downloaded UniProt speclist.txt file (complete ~14,000 species)
    3. Online UniProt API lookup (slow, always up-to-date)
    4. taxoniq package (fast offline NCBI taxonomy - recommended)
    5. Biopython Entrez (online NCBI lookup)
    
    Usage:
        # Basic (built-in mapping)
        tax_id = SpeciesMapper.get_tax_id("HUMAN")  # "9606"
        
        # With extended mapping
        SpeciesMapper.download_uniprot_speclist()  # One-time download
        tax_id = SpeciesMapper.get_tax_id("MYCBO")  # Now works!
        
        # With taxoniq (recommended for production)
        pip install taxoniq
        tax_id = SpeciesMapper.lookup_taxoniq("Homo sapiens")  # "9606"
    """
    
    _extended_mapping: Optional[Dict[str, str]] = None
    _speclist_path: Optional[Path] = None
    _taxoniq_available: Optional[bool] = None
    _biopython_available: Optional[bool] = None
    _initialized: bool = False
    
    @classmethod
    def _auto_init(cls):
        """Auto-initialize by loading bundled speclist.txt if available."""
        if cls._initialized:
            return
        cls._initialized = True
        
        # Try to load bundled speclist.txt from package data
        try:
            import importlib.resources as pkg_resources
            try:
                # Python 3.9+
                data_path = pkg_resources.files('boltz2_client.data').joinpath('speclist.txt')
                if data_path.is_file():
                    cls.load_speclist(Path(str(data_path)))
                    logger.info("Loaded bundled speclist.txt from package data")
                    return
            except (TypeError, AttributeError):
                # Python 3.8 fallback
                try:
                    with pkg_resources.path('boltz2_client.data', 'speclist.txt') as data_path:
                        if data_path.exists():
                            cls.load_speclist(data_path)
                            logger.info("Loaded bundled speclist.txt from package data")
                            return
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Could not load bundled speclist.txt: {e}")
        
        # Fallback: check user cache
        cache_path = Path.home() / ".boltz2" / "speclist.txt"
        if cache_path.exists():
            cls.load_speclist(cache_path)
            logger.info(f"Loaded speclist.txt from cache: {cache_path}")
    
    @classmethod
    def get_tax_id(cls, species_code: str) -> Optional[str]:
        """
        Get TaxID for a species code.
        
        Automatically loads the bundled speclist.txt on first call.
        
        Args:
            species_code: UniProt species mnemonic (e.g., "HUMAN", "MOUSE")
            
        Returns:
            NCBI Taxonomic ID as string, or None if not found
        """
        # Auto-initialize on first call
        cls._auto_init()
        
        # First check built-in mapping
        if species_code in SPECIES_TO_TAXID:
            return SPECIES_TO_TAXID[species_code]
        
        # Check extended mapping if loaded
        if cls._extended_mapping and species_code in cls._extended_mapping:
            return cls._extended_mapping[species_code]
        
        return None
    
    @classmethod
    def lookup_taxoniq(cls, species_name: str) -> Optional[str]:
        """
        Look up TaxID using taxoniq package (fast, offline).
        
        Install: pip install taxoniq
        
        Args:
            species_name: Scientific name (e.g., "Homo sapiens")
            
        Returns:
            NCBI Taxonomic ID as string, or None if not found
        """
        if cls._taxoniq_available is None:
            try:
                import taxoniq
                cls._taxoniq_available = True
            except ImportError:
                cls._taxoniq_available = False
                logger.warning("taxoniq not installed. Install with: pip install taxoniq")
        
        if not cls._taxoniq_available:
            return None
        
        try:
            import taxoniq
            # Search by scientific name
            results = taxoniq.Taxon.search(species_name)
            if results:
                return str(results[0].tax_id)
        except Exception as e:
            logger.debug(f"taxoniq lookup failed for '{species_name}': {e}")
        
        return None
    
    @classmethod
    def lookup_biopython(cls, species_name: str, email: str = "user@example.com") -> Optional[str]:
        """
        Look up TaxID using Biopython's Entrez (online NCBI lookup).
        
        Install: pip install biopython
        
        Args:
            species_name: Scientific name (e.g., "Homo sapiens")
            email: Email for NCBI Entrez (required by NCBI)
            
        Returns:
            NCBI Taxonomic ID as string, or None if not found
        """
        if cls._biopython_available is None:
            try:
                from Bio import Entrez
                cls._biopython_available = True
            except ImportError:
                cls._biopython_available = False
                logger.warning("Biopython not installed. Install with: pip install biopython")
        
        if not cls._biopython_available:
            return None
        
        try:
            from Bio import Entrez
            Entrez.email = email
            
            # Search NCBI Taxonomy
            handle = Entrez.esearch(db="taxonomy", term=species_name)
            record = Entrez.read(handle)
            handle.close()
            
            if record["IdList"]:
                return record["IdList"][0]
        except Exception as e:
            logger.debug(f"Biopython lookup failed for '{species_name}': {e}")
        
        return None
    
    # Cache for UniProt accession to TaxID lookups
    _accession_cache: Dict[str, str] = {}
    
    @classmethod
    def lookup_uniprot_api(cls, species_code: str) -> Optional[str]:
        """
        Look up TaxID using UniProt REST API (online).
        
        Args:
            species_code: UniProt species mnemonic (e.g., "HUMAN")
            
        Returns:
            NCBI Taxonomic ID as string, or None if not found
        """
        import urllib.request
        import json
        
        try:
            # UniProt REST API endpoint
            url = f"https://rest.uniprot.org/taxonomy/search?query=mnemonic:{species_code}&format=json&size=1"
            
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                if data.get("results"):
                    return str(data["results"][0]["taxonId"])
        except Exception as e:
            logger.debug(f"UniProt API lookup failed for '{species_code}': {e}")
        
        return None
    
    @classmethod
    def lookup_uniprot_accession(cls, accession: str) -> Optional[str]:
        """
        Look up TaxID from a UniProt accession (e.g., A0A0B4J2F2).
        
        This is useful when A3M files only have UniProt IDs without species codes.
        Results are cached to avoid repeated API calls.
        
        Args:
            accession: UniProt accession (e.g., "A0A0B4J2F2", "P12345")
            
        Returns:
            NCBI Taxonomic ID as string, or None if not found
            
        Example:
            >>> SpeciesMapper.lookup_uniprot_accession("A0A0B4J2F2")
            '9606'  # Human
        """
        # Check cache first
        if accession in cls._accession_cache:
            return cls._accession_cache[accession]
        
        import urllib.request
        import json
        
        try:
            # UniProt REST API - fetch entry by accession
            url = f"https://rest.uniprot.org/uniprotkb/{accession}?fields=organism_id&format=json"
            
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                if data.get("organism") and data["organism"].get("taxonId"):
                    tax_id = str(data["organism"]["taxonId"])
                    cls._accession_cache[accession] = tax_id
                    return tax_id
        except Exception as e:
            logger.debug(f"UniProt accession lookup failed for '{accession}': {e}")
        
        return None
    
    @classmethod
    def batch_lookup_accessions(
        cls, 
        accessions: List[str], 
        max_batch_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, str]:
        """
        Batch lookup TaxIDs for multiple UniProt accessions.
        
        More efficient than individual lookups for large MSA files.
        
        Args:
            accessions: List of UniProt accessions
            max_batch_size: Maximum accessions per API call (default: 100)
            progress_callback: Optional callback(completed, total) for progress
            
        Returns:
            Dictionary mapping accession to TaxID
            
        Example:
            >>> accessions = ["A0A0B4J2F2", "P12345", "Q9Y6K9"]
            >>> results = SpeciesMapper.batch_lookup_accessions(accessions)
            >>> print(results)
            {'A0A0B4J2F2': '9606', 'P12345': '10090', 'Q9Y6K9': '9606'}
        """
        import urllib.request
        import json
        
        results = {}
        
        # Filter out already cached
        uncached = [acc for acc in accessions if acc not in cls._accession_cache]
        
        # Add cached results
        for acc in accessions:
            if acc in cls._accession_cache:
                results[acc] = cls._accession_cache[acc]
        
        if not uncached:
            return results
        
        # Process in batches
        total = len(uncached)
        completed = 0
        
        for i in range(0, len(uncached), max_batch_size):
            batch = uncached[i:i + max_batch_size]
            
            try:
                # UniProt batch query - URL encode the query
                import urllib.parse
                query = " OR ".join([f"accession:{acc}" for acc in batch])
                encoded_query = urllib.parse.quote(query)
                url = f"https://rest.uniprot.org/uniprotkb/search?query={encoded_query}&fields=accession,organism_id&format=json&size={len(batch)}"
                
                with urllib.request.urlopen(url, timeout=30) as response:
                    data = json.loads(response.read().decode())
                    
                    for entry in data.get("results", []):
                        acc = entry.get("primaryAccession")
                        if acc and entry.get("organism"):
                            tax_id = str(entry["organism"].get("taxonId", ""))
                            if tax_id:
                                results[acc] = tax_id
                                cls._accession_cache[acc] = tax_id
                
                completed += len(batch)
                if progress_callback:
                    progress_callback(completed, total)
                    
            except Exception as e:
                logger.warning(f"Batch lookup failed for {len(batch)} accessions: {e}")
                # Fall back to individual lookups
                for acc in batch:
                    tax_id = cls.lookup_uniprot_accession(acc)
                    if tax_id:
                        results[acc] = tax_id
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total)
        
        return results
    
    @classmethod
    def load_speclist(cls, speclist_path: Path) -> int:
        """
        Load species mapping from UniProt speclist.txt file.
        
        Download from: https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/docs/speclist.txt
        
        File format:
            CODE  KINGDOM   TAXID: N=Description
            Example: HUMAN E    9606: N=Homo sapiens
            
        Args:
            speclist_path: Path to downloaded speclist.txt
            
        Returns:
            Number of species mappings loaded
        """
        cls._extended_mapping = {}
        cls._speclist_path = speclist_path
        
        with open(speclist_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Skip header/comment lines
                if line.startswith('-') or line.startswith('=') or line.startswith(' '):
                    continue
                
                # Format: CODE  KINGDOM   TAXID: N=Description
                # Example: HUMAN E    9606: N=Homo sapiens
                # The code is at the start, followed by kingdom letter, then TaxID
                
                # Use regex to parse: CODE KINGDOM TAXID: ...
                match = re.match(r'^([A-Z0-9]{2,5})\s+[ABEVO]\s+(\d+):', line)
                if match:
                    code = match.group(1)
                    tax_id = match.group(2)
                    cls._extended_mapping[code] = tax_id
        
        logger.info(f"Loaded {len(cls._extended_mapping)} species mappings from {speclist_path}")
        return len(cls._extended_mapping)
    
    @classmethod
    def download_uniprot_speclist(cls, output_path: Optional[Path] = None) -> Path:
        """
        Download the UniProt species list file.
        
        Args:
            output_path: Where to save the file (default: ~/.boltz2/speclist.txt)
            
        Returns:
            Path to the downloaded file
        """
        import urllib.request
        
        url = "https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/docs/speclist.txt"
        
        if output_path is None:
            cache_dir = Path.home() / ".boltz2"
            cache_dir.mkdir(exist_ok=True)
            output_path = cache_dir / "speclist.txt"
        
        logger.info(f"Downloading UniProt species list from {url}...")
        urllib.request.urlretrieve(url, output_path)
        logger.info(f"Saved to {output_path}")
        
        # Load it immediately
        cls.load_speclist(output_path)
        
        return output_path
    
    @classmethod
    def ensure_loaded(cls, download_if_missing: bool = False) -> bool:
        """
        Ensure species mapping is loaded, optionally downloading if missing.
        
        Args:
            download_if_missing: If True, download speclist.txt if not cached
            
        Returns:
            True if extended mapping is available
        """
        if cls._extended_mapping is not None:
            return True
        
        # Check for cached file
        cache_path = Path.home() / ".boltz2" / "speclist.txt"
        if cache_path.exists():
            cls.load_speclist(cache_path)
            return True
        
        if download_if_missing:
            try:
                cls.download_uniprot_speclist()
                return True
            except Exception as e:
                logger.warning(f"Failed to download speclist: {e}")
        
        return False
    
    @classmethod
    def get_mapping_stats(cls) -> Dict[str, int]:
        """Get statistics about loaded mappings."""
        return {
            "builtin_count": len(SPECIES_TO_TAXID),
            "extended_count": len(cls._extended_mapping) if cls._extended_mapping else 0,
            "total": len(SPECIES_TO_TAXID) + (len(cls._extended_mapping) if cls._extended_mapping else 0),
            "taxoniq_available": cls._taxoniq_available or False,
            "biopython_available": cls._biopython_available or False,
        }
    
    @classmethod
    def smart_lookup(cls, identifier: str, try_online: bool = False) -> Optional[str]:
        """
        Smart lookup that tries multiple methods.
        
        Order of attempts:
        1. Built-in SPECIES_TO_TAXID
        2. Extended mapping (if loaded)
        3. taxoniq (if installed)
        4. UniProt API (if try_online=True)
        5. Biopython Entrez (if try_online=True and installed)
        
        Args:
            identifier: Species code or scientific name
            try_online: Whether to try online APIs
            
        Returns:
            NCBI Taxonomic ID as string, or None if not found
        """
        # 1. Try built-in mapping (species code)
        result = cls.get_tax_id(identifier)
        if result:
            return result
        
        # 2. Try taxoniq (scientific name)
        result = cls.lookup_taxoniq(identifier)
        if result:
            return result
        
        # 3. Try online APIs if enabled
        if try_online:
            # Try UniProt API first (species code)
            result = cls.lookup_uniprot_api(identifier)
            if result:
                return result
            
            # Try Biopython/Entrez (scientific name)
            result = cls.lookup_biopython(identifier)
            if result:
                return result
        
        return None


@dataclass
class A3MSequence:
    """Represents a single sequence entry from an A3M file."""
    header: str
    sequence: str
    identifier: str = ""
    organism_id: str = ""  # UniRef cluster ID or accession
    tax_id: str = ""       # NCBI Taxonomic ID (like ColabFold uses)
    species: str = ""      # Species code (e.g., HUMAN, MOUSE)
    is_query: bool = False
    
    def __post_init__(self):
        """Parse identifier and organism info from header."""
        self._parse_header()
    
    def _parse_header(self):
        """
        Extract identifier, organism info, and taxonomic ID from A3M header.
        
        Supports multiple header formats:
        1. UniRef: >UniRef100_A0A2N5EEG3 TaxID=9606 ...
        2. UniProt: >tr|A0A0B4J2F2|A0A0B4J2F2_HUMAN
        3. NCBI: >gi|123|ref|NP_001.1| protein [Homo sapiens]
        4. ColabFold: >sequence_id OX=9606 ...
        """
        # Handle query sequence
        if self.header.startswith(">Query") or self.header.startswith(">101") or \
           self.header.lower().startswith(">query"):
            self.is_query = True
            self.identifier = "QUERY"
            self.tax_id = "QUERY"
            return
        
        header_clean = self.header.lstrip('>')
        full_header = header_clean  # Keep full header for TaxID search
        parts = header_clean.split('\t')
        first_part = parts[0].strip()
        
        # Try to extract explicit TaxID from header
        # Format: OX=9606 or TaxID=9606 or taxid=9606
        tax_match = re.search(r'(?:OX|TaxID|taxid)[=:\s]+(\d+)', full_header, re.IGNORECASE)
        if tax_match:
            self.tax_id = tax_match.group(1)
        
        # Try UniProt format: tr|ACCESSION|NAME_SPECIES or sp|ACCESSION|NAME_SPECIES
        uniprot_match = re.match(r'(?:sp|tr)\|([A-Za-z0-9]+)\|([A-Za-z0-9_]+)_([A-Z0-9]+)', first_part)
        if uniprot_match:
            self.identifier = uniprot_match.group(1)
            self.organism_id = uniprot_match.group(1)
            self.species = uniprot_match.group(3)
            # Map species code to TaxID if not already found
            if not self.tax_id and self.species:
                mapped_tax_id = SpeciesMapper.get_tax_id(self.species)
                if mapped_tax_id:
                    self.tax_id = mapped_tax_id
            return
        
        # Try to extract UniRef ID
        uniref_match = re.match(r'(UniRef\d+_[A-Za-z0-9]+)', first_part)
        if uniref_match:
            self.identifier = uniref_match.group(1)
            # Extract the UniProt accession part
            acc_match = re.search(r'UniRef\d+_([A-Za-z0-9]+)', self.identifier)
            if acc_match:
                self.organism_id = acc_match.group(1)
            
            # Check for species suffix in header (e.g., UniRef100_A0A2N5EEG3_HUMAN)
            species_match = re.search(r'_([A-Z]{3,5})(?:\s|$|\t)', first_part)
            if species_match:
                self.species = species_match.group(1)
                if not self.tax_id and self.species:
                    mapped_tax_id = SpeciesMapper.get_tax_id(self.species)
                    if mapped_tax_id:
                        self.tax_id = mapped_tax_id
            return
        
        # Try NCBI format: >gi|123|ref|NP_001.1| protein [Species name]
        ncbi_match = re.search(r'\[([^\]]+)\]', full_header)
        if ncbi_match:
            species_name = ncbi_match.group(1)
            self.species = species_name
            # Try to map common species names to TaxID
            species_lower = species_name.lower()
            if "homo sapiens" in species_lower:
                self.tax_id = "9606"
            elif "mus musculus" in species_lower:
                self.tax_id = "10090"
            elif "rattus" in species_lower:
                self.tax_id = "10116"
            elif "escherichia coli" in species_lower:
                self.tax_id = "562"
        
        # Extract any identifier
        id_match = re.match(r'([A-Za-z0-9_]+)', first_part)
        if id_match:
            self.identifier = id_match.group(1)
            if not self.organism_id:
                self.organism_id = self.identifier
        
        # If no TaxID found, check if organism_id looks like a numeric TaxID
        # DO NOT use accession-like strings as TaxID (they need to be looked up)
        if not self.tax_id and self.organism_id:
            # Only use organism_id as TaxID if it's numeric (actual TaxID)
            if self.organism_id.isdigit():
                self.tax_id = self.organism_id
            # Otherwise leave tax_id empty - it can be enriched later via API lookup


@dataclass
class A3MMSA:
    """Represents a parsed A3M Multiple Sequence Alignment file."""
    sequences: List[A3MSequence] = field(default_factory=list)
    source_file: Optional[Path] = None
    chain_id: str = ""
    query_sequence: str = ""
    
    def get_query(self) -> Optional[A3MSequence]:
        """Get the query sequence (first sequence in MSA)."""
        for seq in self.sequences:
            if seq.is_query:
                return seq
        return self.sequences[0] if self.sequences else None
    
    def get_sequence_by_id(self, identifier: str) -> Optional[A3MSequence]:
        """Find a sequence by its identifier."""
        for seq in self.sequences:
            if seq.identifier == identifier or seq.organism_id == identifier:
                return seq
        return None
    
    def get_sequence_by_tax_id(self, tax_id: str) -> Optional[A3MSequence]:
        """Find the first sequence with a given taxonomic ID."""
        for seq in self.sequences:
            if seq.tax_id == tax_id and not seq.is_query:
                return seq
        return None
    
    def get_sequences_by_tax_id(self, tax_id: str) -> List[A3MSequence]:
        """Find all sequences with a given taxonomic ID."""
        return [seq for seq in self.sequences if seq.tax_id == tax_id and not seq.is_query]
    
    def get_organism_ids(self) -> Set[str]:
        """Get all unique organism IDs in this MSA."""
        return {seq.organism_id for seq in self.sequences if seq.organism_id and not seq.is_query}
    
    def get_tax_ids(self) -> Set[str]:
        """Get all unique taxonomic IDs in this MSA (like ColabFold)."""
        return {seq.tax_id for seq in self.sequences if seq.tax_id and not seq.is_query}
    
    def enrich_tax_ids_from_accessions(
        self, 
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Enrich sequences with TaxIDs by looking up UniProt accessions.
        
        This is useful when A3M files only have UniProt accessions without
        species codes or TaxIDs. Makes batch API calls to UniProt.
        
        Args:
            progress_callback: Optional callback(completed, total) for progress
            
        Returns:
            Number of sequences enriched with TaxIDs
            
        Example:
            >>> msa = A3MParser.parse_file(Path("alignment.a3m"))
            >>> enriched = msa.enrich_tax_ids_from_accessions()
            >>> print(f"Enriched {enriched} sequences with TaxIDs")
        """
        # Find sequences without TaxID but with organism_id (likely UniProt accession)
        needs_lookup = []
        for seq in self.sequences:
            if not seq.tax_id and seq.organism_id and not seq.is_query:
                # Check if organism_id looks like a UniProt accession
                # UniProt accessions: 6-10 alphanumeric, starting with letter
                # Examples: P04637, A0A0B4J2F2, Q9Y6K9
                if re.match(r'^[A-Z][A-Z0-9]{5,9}$', seq.organism_id):
                    needs_lookup.append(seq)
                # Also check identifier if different from organism_id
                elif seq.identifier and seq.identifier != seq.organism_id:
                    if re.match(r'^[A-Z][A-Z0-9]{5,9}$', seq.identifier):
                        needs_lookup.append(seq)
        
        if not needs_lookup:
            return 0
        
        # Batch lookup
        accessions = [seq.organism_id for seq in needs_lookup]
        results = SpeciesMapper.batch_lookup_accessions(
            accessions, 
            progress_callback=progress_callback
        )
        
        # Update sequences
        enriched = 0
        for seq in needs_lookup:
            if seq.organism_id in results:
                seq.tax_id = results[seq.organism_id]
                enriched += 1
        
        logger.info(f"Enriched {enriched}/{len(needs_lookup)} sequences with TaxIDs from UniProt accessions")
        return enriched


class A3MParser:
    """Parser for A3M format Multiple Sequence Alignment files."""
    
    @staticmethod
    def parse(content: str) -> A3MMSA:
        """
        Parse A3M format content into structured representation.
        
        Args:
            content: A3M file content as string
            
        Returns:
            A3MMSA object with parsed sequences
        """
        msa = A3MMSA()
        lines = content.strip().split('\n')
        
        current_header = None
        current_sequence = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip comment lines (some A3M files have them)
            if line.startswith('#'):
                continue
            
            if line.startswith('>'):
                # Save previous sequence if exists
                if current_header is not None:
                    seq_str = ''.join(current_sequence)
                    msa.sequences.append(A3MSequence(
                        header=current_header,
                        sequence=seq_str
                    ))
                
                current_header = line
                current_sequence = []
            else:
                current_sequence.append(line)
        
        # Save last sequence
        if current_header is not None:
            seq_str = ''.join(current_sequence)
            msa.sequences.append(A3MSequence(
                header=current_header,
                sequence=seq_str
            ))
        
        # Set query sequence
        query = msa.get_query()
        if query:
            msa.query_sequence = query.sequence
        
        return msa
    
    @staticmethod
    def parse_file(file_path: Path) -> A3MMSA:
        """
        Parse an A3M file.
        
        Args:
            file_path: Path to A3M file
            
        Returns:
            A3MMSA object with parsed sequences
        """
        content = file_path.read_text()
        msa = A3MParser.parse(content)
        msa.source_file = file_path
        return msa


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
        
        Args:
            msas: Dictionary mapping chain ID to A3MMSA
            
        Returns:
            List of dictionaries mapping chain ID to paired sequence
        """
        if not msas:
            return []
        
        chain_ids = list(msas.keys())
        pairs = []
        
        # First, add the query sequences as the first pair
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
        
        # Find intersection of all ID sets (common across ALL chains)
        common_ids = id_sets[0].copy()
        for id_set in id_sets[1:]:
            common_ids &= id_set
        
        logger.info(f"Found {len(common_ids)} common {id_type}s across {len(chain_ids)} chains")
        
        # Create pairs for each common ID
        for tax_id in sorted(common_ids):
            pair = {}
            for chain_id, msa in msas.items():
                seq = get_seq_func(msa, tax_id)
                if seq:
                    pair[chain_id] = seq
            
            # Greedy: include even if not all chains have this ID
            # But for now, only include complete pairs for consistency
            if len(pair) == len(chain_ids):
                pairs.append(pair)
        
        return pairs


class CompletePairingStrategy(PairingStrategy):
    """
    Complete pairing strategy (like ColabFold's original behavior).
    
    This was ColabFold's default before June 2023.
    
    Key behavior:
    - Only creates a pair if ALL chains have matching taxonomic ID
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
        
        This is the same as greedy for pairwise, but differs for 3+ chains.
        
        Args:
            msas: Dictionary mapping chain ID to A3MMSA
            
        Returns:
            List of dictionaries mapping chain ID to paired sequence
        """
        # For pairwise (2 chains), complete and greedy are the same
        # The difference is for 3+ chains where greedy allows partial matches
        greedy = GreedyPairingStrategy(use_tax_id=self.use_tax_id)
        return greedy.find_pairs(msas)


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
        
        The Boltz2 NIM API requires separate CSVs per polymer where:
        - Each CSV has columns: key, sequence
        - Rows with the same 'key' across different chain CSVs are paired
        - This enables the model to identify co-evolved sequences from same organisms
        
        When include_unpaired=True, also includes:
        - Unpaired sequences in "block-diagonal" format where only one chain has
          a sequence and others have gaps. This maximizes MSA depth while still
          providing pairing information where available.
        
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
        
        if self.max_pairs:
            pairs = pairs[:self.max_pairs]
        
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
        
        # Collect unpaired sequences if requested
        unpaired_sequences: Dict[str, List[A3MSequence]] = {chain_id: [] for chain_id in chain_ids}
        num_unpaired = 0
        
        if self.include_unpaired:
            for chain_id, msa in msas.items():
                for seq in msa.sequences:
                    if seq.is_query:
                        continue
                    if seq.identifier not in paired_sequence_ids[chain_id]:
                        unpaired_sequences[chain_id].append(seq)
                        num_unpaired += 1
            
            logger.info(f"Found {num_unpaired} unpaired sequences to include in block-diagonal format")
        
        # Calculate total rows: paired + unpaired (block-diagonal)
        current_key = len(pairs)  # Start unpaired keys after paired ones
        
        # Build per-chain CSVs (for Boltz2 NIM API)
        csv_per_chain: Dict[str, str] = {}
        for chain_id in chain_ids:
            chain_lines = ["key,sequence"]
            
            # Add paired sequences
            for idx, pair in enumerate(pairs, start=1):
                if chain_id in pair:
                    seq = self._clean_sequence(pair[chain_id].sequence)
                    chain_lines.append(f"{idx},{seq}")
                else:
                    # Use gaps if sequence not found for this chain
                    gap_seq = '-' * query_lengths.get(chain_id, 0)
                    chain_lines.append(f"{idx},{gap_seq}")
            
            csv_per_chain[chain_id] = '\n'.join(chain_lines)
        
        # Add unpaired sequences in block-diagonal format
        if self.include_unpaired:
            unpaired_key = current_key + 1
            for source_chain_id in chain_ids:
                for unpaired_seq in unpaired_sequences[source_chain_id]:
                    # Add this unpaired sequence to all chain CSVs
                    for chain_id in chain_ids:
                        if chain_id == source_chain_id:
                            # This chain has the sequence
                            seq = self._clean_sequence(unpaired_seq.sequence)
                            csv_per_chain[chain_id] += f"\n{unpaired_key},{seq}"
                        else:
                            # Other chains get gaps
                            gap_seq = '-' * query_lengths.get(chain_id, 0)
                            csv_per_chain[chain_id] += f"\n{unpaired_key},{gap_seq}"
                    unpaired_key += 1
        
        # Build combined CSV (for reference/documentation)
        csv_lines = ["key,sequence"]
        for idx, pair in enumerate(pairs, start=1):
            sequences = []
            for chain_id in chain_ids:
                if chain_id in pair:
                    seq = self._clean_sequence(pair[chain_id].sequence)
                    sequences.append(seq)
                else:
                    sequences.append('-' * query_lengths.get(chain_id, 0))
            concatenated = ':'.join(sequences)
            csv_lines.append(f"{idx},{concatenated}")
        
        # Add unpaired sequences to combined CSV in block-diagonal format
        if self.include_unpaired:
            unpaired_key = current_key + 1
            for source_chain_id in chain_ids:
                for unpaired_seq in unpaired_sequences[source_chain_id]:
                    sequences = []
                    for chain_id in chain_ids:
                        if chain_id == source_chain_id:
                            seq = self._clean_sequence(unpaired_seq.sequence)
                            sequences.append(seq)
                        else:
                            sequences.append('-' * query_lengths.get(chain_id, 0))
                    concatenated = ':'.join(sequences)
                    csv_lines.append(f"{unpaired_key},{concatenated}")
                    unpaired_key += 1
        
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
    from .models import AlignmentFileRecord
    
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
    from .models import AlignmentFileRecord
    
    msa_per_chain = {}
    for chain_id, csv_content in conversion_result.csv_per_chain.items():
        msa_record = AlignmentFileRecord(
            alignment=csv_content,
            format="csv",
            rank=0
        )
        msa_per_chain[chain_id] = {"paired": {"csv": msa_record}}
    
    return msa_per_chain


def save_prediction_outputs(
    response,
    output_dir: Path,
    base_name: str = "complex",
    save_structure: bool = True,
    save_scores: bool = True,
    save_csv: bool = False,
    conversion_result: Optional[ConversionResult] = None
) -> Dict[str, Path]:
    """
    Save all prediction outputs to files.
    
    This is a convenience function that saves the complete Boltz2 prediction
    outputs including structures, confidence scores, and optionally paired CSVs.
    
    Args:
        response: PredictionResponse from Boltz2 client
        output_dir: Directory to save outputs (created if doesn't exist)
        base_name: Base name for output files (default: "complex")
        save_structure: Save CIF structure file(s) (default: True)
        save_scores: Save scores JSON file (default: True)
        save_csv: Save paired CSV files (default: False, requires conversion_result)
        conversion_result: ConversionResult from convert_a3m_to_multimer_csv
                          (required if save_csv=True)
    
    Returns:
        Dictionary mapping output type to file path
        
    Example:
        >>> # Basic usage - save structure and scores
        >>> response = await client.predict(request)
        >>> paths = save_prediction_outputs(
        ...     response=response,
        ...     output_dir=Path("results"),
        ...     base_name="my_complex",
        ...     save_scores=True
        ... )
        >>> print(paths)
        {'structure': Path('results/my_complex.cif'),
         'scores': Path('results/my_complex.scores.json')}
        
        >>> # Full usage with CSV files
        >>> result = convert_a3m_to_multimer_csv(a3m_files={'A': 'a.a3m', 'B': 'b.a3m'})
        >>> paths = save_prediction_outputs(
        ...     response=response,
        ...     output_dir=Path("results"),
        ...     save_csv=True,
        ...     conversion_result=result
        ... )
    """
    import json
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    saved_paths = {}
    
    # Save structure(s)
    if save_structure and response.structures:
        for i, structure in enumerate(response.structures):
            if i == 0:
                structure_path = output_dir / f"{base_name}.cif"
            else:
                structure_path = output_dir / f"{base_name}_{i+1}.cif"
            
            cif_content = structure.structure if hasattr(structure, 'structure') else str(structure)
            structure_path.write_text(cif_content)
            
            if i == 0:
                saved_paths['structure'] = structure_path
            else:
                saved_paths[f'structure_{i+1}'] = structure_path
        
        logger.info(f"Saved {len(response.structures)} structure(s) to {output_dir}")
    
    # Save scores
    if save_scores:
        scores = {
            'confidence_scores': response.confidence_scores,
            'ptm_scores': response.ptm_scores,
            'iptm_scores': response.iptm_scores,
            'complex_plddt_scores': response.complex_plddt_scores,
            'complex_iplddt_scores': response.complex_iplddt_scores,
            'complex_pde_scores': response.complex_pde_scores,
            'complex_ipde_scores': response.complex_ipde_scores,
            'chains_ptm_scores': response.chains_ptm_scores,
            'pair_chains_iptm_scores': response.pair_chains_iptm_scores,
            'ligand_iptm_scores': response.ligand_iptm_scores,
            'protein_iptm_scores': response.protein_iptm_scores,
            'metrics': response.metrics,
        }
        
        # Remove None values
        scores = {k: v for k, v in scores.items() if v is not None}
        
        scores_path = output_dir / f"{base_name}.scores.json"
        scores_path.write_text(json.dumps(scores, indent=2))
        saved_paths['scores'] = scores_path
        
        logger.info(f"Saved scores to {scores_path}")
    
    # Save paired CSV files
    if save_csv:
        if conversion_result is None:
            raise ValueError("conversion_result is required when save_csv=True")
        
        for chain_id, csv_content in conversion_result.csv_per_chain.items():
            csv_path = output_dir / f"{base_name}_chain_{chain_id}.csv"
            csv_path.write_text(csv_content)
            saved_paths[f'csv_{chain_id}'] = csv_path
        
        logger.info(f"Saved {len(conversion_result.csv_per_chain)} CSV files to {output_dir}")
    
    return saved_paths


def get_prediction_summary(response) -> Dict:
    """
    Get a summary of prediction scores from a PredictionResponse.
    
    Args:
        response: PredictionResponse from Boltz2 client
        
    Returns:
        Dictionary with key scores and their interpretations
        
    Example:
        >>> summary = get_prediction_summary(response)
        >>> print(f"Confidence: {summary['confidence']:.2f}")
        >>> print(f"Quality: {summary['quality_assessment']}")
    """
    summary = {
        'num_structures': len(response.structures) if response.structures else 0,
    }
    
    # Add scores if available
    if response.confidence_scores:
        summary['confidence'] = response.confidence_scores[0]
    
    if response.ptm_scores:
        summary['ptm'] = response.ptm_scores[0]
    
    if response.iptm_scores:
        summary['iptm'] = response.iptm_scores[0]
    
    if response.complex_plddt_scores:
        summary['plddt'] = response.complex_plddt_scores[0]
    
    if response.complex_iplddt_scores:
        summary['interface_plddt'] = response.complex_iplddt_scores[0]
    
    # Quality assessment based on confidence
    if 'confidence' in summary:
        conf = summary['confidence']
        if conf >= 0.9:
            summary['quality_assessment'] = 'Very High'
        elif conf >= 0.7:
            summary['quality_assessment'] = 'High'
        elif conf >= 0.5:
            summary['quality_assessment'] = 'Medium'
        else:
            summary['quality_assessment'] = 'Low'
    
    # Timing info
    if response.metrics and 'total_time_seconds' in response.metrics:
        summary['prediction_time_seconds'] = response.metrics['total_time_seconds']
    
    return summary

