# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
A3M file parsing and species taxonomy mapping.

Provides classes for parsing A3M MSA files, extracting taxonomic IDs,
and mapping UniProt species codes to NCBI Taxonomy IDs.

Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set, Union
from pathlib import Path
from dataclasses import dataclass, field

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

