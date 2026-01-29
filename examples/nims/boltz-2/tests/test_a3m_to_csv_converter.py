#!/usr/bin/env python3
"""
Tests for A3M to CSV Multimer MSA Converter.

Tests cover:
1. A3M parsing (headers, sequences, various formats)
2. Pairing strategies (greedy, complete)
3. TaxID vs UniRef ID pairing
4. CSV generation
5. Block-diagonal unpaired sequences (new feature)
"""

import pytest
from pathlib import Path
from boltz2_client.a3m_to_csv_converter import (
    A3MParser,
    A3MMSA,
    A3MSequence,
    A3MToCSVConverter,
    GreedyPairingStrategy,
    CompletePairingStrategy,
    TaxonomyPairingStrategy,
    SpeciesMapper,
    convert_a3m_to_multimer_csv,
    create_paired_msa_per_chain,
    ConversionResult,
    SPECIES_TO_TAXID,
)


# Test data
CHAIN_A_A3M = """>Query|-|Query
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
>UniRef100_A0A2N5EEG3	340	0.994
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
>UniRef100_UPI000755DEB5	340	0.994
MKTVRQERLKSIVRILERSKDPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
>UniRef100_Q54321	320	0.95
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLG
>UniRef100_B67890	315	0.90
MKTVRQERLKSIVRILERSKEPVSGAQLAEDLSVSRQVIVQDIAYLRSLG
"""

CHAIN_B_A3M = """>Query|-|Query
MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAEAPAD
>UniRef100_A0A2N5EEG3	340	0.994
MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAEAPAD
>UniRef100_UPI000755DEB5	340	0.994
MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAERPAD
>UniRef100_X99999	300	0.85
MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAE
>UniRef100_B67890	315	0.90
MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAEAPAD
"""

# A3M with TaxID annotations
CHAIN_A_TAXID_A3M = """>Query|-|Query
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
>tr|A0A0B4J2F2|A0A0B4J2F2_HUMAN
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
>tr|P12345|P12345_MOUSE
MKTVRQERLKSIVRILERSKDPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
>UniRef100_XYZ123 OX=7955
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLG
"""

CHAIN_B_TAXID_A3M = """>Query|-|Query
MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAEAPAD
>tr|Q99999|Q99999_HUMAN
MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAEAPAD
>tr|Q54321|Q54321_MOUSE
MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAERPAD
>UniRef100_ABC456 OX=7955
MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAE
"""


class TestA3MParser:
    """Tests for A3M file parsing."""
    
    def test_parse_basic(self):
        """Test basic A3M parsing."""
        msa = A3MParser.parse(CHAIN_A_A3M)
        
        assert len(msa.sequences) == 5
        assert msa.sequences[0].is_query == True
        
    def test_parse_query_sequence(self):
        """Test query sequence identification."""
        msa = A3MParser.parse(CHAIN_A_A3M)
        
        query = msa.get_query()
        assert query is not None
        assert query.is_query == True
        assert len(query.sequence) == 65  # Actual length of test sequence
        
    def test_parse_uniref_headers(self):
        """Test parsing UniRef-style headers."""
        msa = A3MParser.parse(CHAIN_A_A3M)
        
        # Skip query, check first UniRef entry
        seq = msa.sequences[1]
        assert seq.identifier == "UniRef100_A0A2N5EEG3"
        assert seq.organism_id == "A0A2N5EEG3"
        
    def test_parse_uniprot_headers(self):
        """Test parsing UniProt-style headers (tr|...|..._SPECIES)."""
        a3m_content = """>Query
MKTVRQERL
>tr|A0A0B4J2F2|A0A0B4J2F2_HUMAN
MKTVRQERL
>sp|P04637|P53_HUMAN
MKTVRQERL
"""
        msa = A3MParser.parse(a3m_content)
        
        assert len(msa.sequences) == 3
        
        # Check UniProt entry parsing
        seq1 = msa.sequences[1]
        assert seq1.identifier == "A0A0B4J2F2"
        assert seq1.species == "HUMAN"
        assert seq1.tax_id == "9606"  # Should map HUMAN -> 9606
        
    def test_parse_ox_field(self):
        """Test parsing explicit OX= taxonomic ID."""
        a3m_content = """>Query
MKTVRQERL
>UniRef100_ABC123 OX=9606 n=5
MKTVRQERL
"""
        msa = A3MParser.parse(a3m_content)
        
        seq = msa.sequences[1]
        assert seq.tax_id == "9606"
        
    def test_get_organism_ids(self):
        """Test getting unique organism IDs."""
        msa = A3MParser.parse(CHAIN_A_A3M)
        
        org_ids = msa.get_organism_ids()
        assert len(org_ids) == 4  # 4 non-query sequences
        assert "A0A2N5EEG3" in org_ids
        assert "UPI000755DEB5" in org_ids
        
    def test_get_tax_ids(self):
        """Test getting unique TaxIDs."""
        msa = A3MParser.parse(CHAIN_A_TAXID_A3M)
        
        tax_ids = msa.get_tax_ids()
        assert "9606" in tax_ids  # HUMAN
        assert "10090" in tax_ids  # MOUSE
        assert "7955" in tax_ids  # From OX= field


class TestA3MSequence:
    """Tests for A3MSequence header parsing."""
    
    def test_uniprot_format(self):
        """Test UniProt format parsing."""
        seq = A3MSequence(
            header=">tr|A0A0B4J2F2|A0A0B4J2F2_HUMAN",
            sequence="MKTVRQERL"
        )
        assert seq.identifier == "A0A0B4J2F2"
        assert seq.species == "HUMAN"
        assert seq.tax_id == "9606"
        
    def test_uniref_format(self):
        """Test UniRef format parsing."""
        seq = A3MSequence(
            header=">UniRef100_A0A2N5EEG3	340	0.994",
            sequence="MKTVRQERL"
        )
        assert seq.identifier == "UniRef100_A0A2N5EEG3"
        assert seq.organism_id == "A0A2N5EEG3"
        
    def test_ox_field_parsing(self):
        """Test OX= field extraction."""
        seq = A3MSequence(
            header=">UniRef100_ABC123 OX=9606 n=5 Tax=Homo sapiens",
            sequence="MKTVRQERL"
        )
        assert seq.tax_id == "9606"
        
    def test_ncbi_format(self):
        """Test NCBI format with [Species name]."""
        seq = A3MSequence(
            header=">gi|123|ref|NP_001.1| protein [Homo sapiens]",
            sequence="MKTVRQERL"
        )
        assert seq.species == "Homo sapiens"
        assert seq.tax_id == "9606"
        

class TestSpeciesMapper:
    """Tests for species code to TaxID mapping."""
    
    def test_builtin_mapping(self):
        """Test built-in species mapping."""
        assert SpeciesMapper.get_tax_id("HUMAN") == "9606"
        assert SpeciesMapper.get_tax_id("MOUSE") == "10090"
        assert SpeciesMapper.get_tax_id("ECOLI") == "562"
        assert SpeciesMapper.get_tax_id("YEAST") == "559292"
        
    def test_unknown_species(self):
        """Test unknown species returns None."""
        assert SpeciesMapper.get_tax_id("UNKNOWN_SPECIES_XYZ") is None
        
    def test_builtin_mapping_coverage(self):
        """Test that built-in mapping has common organisms."""
        assert "HUMAN" in SPECIES_TO_TAXID
        assert "MOUSE" in SPECIES_TO_TAXID
        assert "ECOLI" in SPECIES_TO_TAXID
        assert "DROME" in SPECIES_TO_TAXID  # Drosophila
        assert "ARATH" in SPECIES_TO_TAXID  # Arabidopsis


class TestPairingStrategies:
    """Tests for sequence pairing strategies."""
    
    def test_greedy_pairing_uniref(self):
        """Test greedy pairing with UniRef IDs."""
        msa_a = A3MParser.parse(CHAIN_A_A3M)
        msa_b = A3MParser.parse(CHAIN_B_A3M)
        
        msa_a.chain_id = 'A'
        msa_b.chain_id = 'B'
        
        strategy = GreedyPairingStrategy(use_tax_id=False)
        pairs = strategy.find_pairs({'A': msa_a, 'B': msa_b})
        
        # Query + 3 common organisms (A0A2N5EEG3, UPI000755DEB5, B67890)
        assert len(pairs) == 4
        
    def test_greedy_pairing_taxid(self):
        """Test greedy pairing with TaxIDs."""
        msa_a = A3MParser.parse(CHAIN_A_TAXID_A3M)
        msa_b = A3MParser.parse(CHAIN_B_TAXID_A3M)
        
        msa_a.chain_id = 'A'
        msa_b.chain_id = 'B'
        
        strategy = GreedyPairingStrategy(use_tax_id=True)
        pairs = strategy.find_pairs({'A': msa_a, 'B': msa_b})
        
        # Query + 3 common TaxIDs (9606/HUMAN, 10090/MOUSE, 7955/zebrafish)
        assert len(pairs) == 4
        
    def test_taxonomy_strategy(self):
        """Test taxonomy-based pairing strategy."""
        msa_a = A3MParser.parse(CHAIN_A_TAXID_A3M)
        msa_b = A3MParser.parse(CHAIN_B_TAXID_A3M)
        
        msa_a.chain_id = 'A'
        msa_b.chain_id = 'B'
        
        strategy = TaxonomyPairingStrategy(strategy="greedy")
        pairs = strategy.find_pairs({'A': msa_a, 'B': msa_b})
        
        assert len(pairs) >= 1  # At least query


class TestA3MToCSVConverter:
    """Tests for the main converter class."""
    
    def test_basic_conversion_with_uniref(self):
        """Test basic conversion with UniRef IDs (use_tax_id=False)."""
        # Use UniRef-based pairing for test data without TaxIDs
        strategy = GreedyPairingStrategy(use_tax_id=False)
        converter = A3MToCSVConverter(pairing_strategy=strategy)
        result = converter.convert_content(
            a3m_contents={'A': CHAIN_A_A3M, 'B': CHAIN_B_A3M}
        )
        
        assert result.num_pairs == 4  # Query + 3 common organisms
        assert len(result.chain_ids) == 2
        assert 'A' in result.csv_per_chain
        assert 'B' in result.csv_per_chain
        
    def test_basic_conversion_with_taxid(self):
        """Test basic conversion with TaxID-based pairing."""
        # Use TaxID-based pairing for data with TaxIDs
        strategy = GreedyPairingStrategy(use_tax_id=True)
        converter = A3MToCSVConverter(pairing_strategy=strategy)
        result = converter.convert_content(
            a3m_contents={'A': CHAIN_A_TAXID_A3M, 'B': CHAIN_B_TAXID_A3M}
        )
        
        # Query + 3 common TaxIDs (9606/HUMAN, 10090/MOUSE, 7955/zebrafish)
        assert result.num_pairs == 4
        
    def test_csv_format(self):
        """Test CSV output format."""
        strategy = GreedyPairingStrategy(use_tax_id=False)
        converter = A3MToCSVConverter(pairing_strategy=strategy)
        result = converter.convert_content(
            a3m_contents={'A': CHAIN_A_A3M, 'B': CHAIN_B_A3M}
        )
        
        # Check CSV header
        assert result.csv_per_chain['A'].startswith('key,sequence')
        assert result.csv_per_chain['B'].startswith('key,sequence')
        
        # Check that keys match across chains
        lines_a = result.csv_per_chain['A'].split('\n')
        lines_b = result.csv_per_chain['B'].split('\n')
        
        keys_a = [line.split(',')[0] for line in lines_a[1:] if line]
        keys_b = [line.split(',')[0] for line in lines_b[1:] if line]
        
        assert keys_a == keys_b  # Keys should match
        
    def test_include_unpaired_false(self):
        """Test that unpaired sequences are excluded by default."""
        strategy = GreedyPairingStrategy(use_tax_id=False)
        converter = A3MToCSVConverter(pairing_strategy=strategy, include_unpaired=False)
        result = converter.convert_content(
            a3m_contents={'A': CHAIN_A_A3M, 'B': CHAIN_B_A3M}
        )
        
        # Count rows (excluding header)
        lines_a = result.csv_per_chain['A'].strip().split('\n')
        assert len(lines_a) == 5  # header + 4 pairs (query + 3 common)
        
    def test_include_unpaired_true(self):
        """Test that unpaired sequences are included in block-diagonal format."""
        strategy = GreedyPairingStrategy(use_tax_id=False)
        converter = A3MToCSVConverter(pairing_strategy=strategy, include_unpaired=True)
        result = converter.convert_content(
            a3m_contents={'A': CHAIN_A_A3M, 'B': CHAIN_B_A3M}
        )
        
        # Count rows (excluding header)
        lines_a = result.csv_per_chain['A'].strip().split('\n')
        
        # Should have: header + 4 paired + unpaired from A (Q54321) + unpaired from B (X99999)
        # Chain A has Q54321 that's not in B
        # Chain B has X99999 that's not in A
        assert len(lines_a) > 5  # More than just paired
        
    def test_unpaired_block_diagonal_format(self):
        """Test that unpaired sequences use gaps for other chains."""
        strategy = GreedyPairingStrategy(use_tax_id=False)
        converter = A3MToCSVConverter(pairing_strategy=strategy, include_unpaired=True)
        result = converter.convert_content(
            a3m_contents={'A': CHAIN_A_A3M, 'B': CHAIN_B_A3M}
        )
        
        # Parse CSVs
        lines_a = result.csv_per_chain['A'].strip().split('\n')
        lines_b = result.csv_per_chain['B'].strip().split('\n')
        
        # Find rows where one chain has gaps
        gap_rows_a = [line for line in lines_a[1:] if ',' in line and line.split(',')[1].startswith('-')]
        gap_rows_b = [line for line in lines_b[1:] if ',' in line and line.split(',')[1].startswith('-')]
        
        # Chain A should have gap rows (for B's unpaired sequences)
        # Chain B should have gap rows (for A's unpaired sequences)
        # At least one chain should have gaps
        assert len(gap_rows_a) > 0 or len(gap_rows_b) > 0
        
    def test_max_pairs_limit(self):
        """Test max_pairs parameter."""
        strategy = GreedyPairingStrategy(use_tax_id=False)
        converter = A3MToCSVConverter(pairing_strategy=strategy, max_pairs=2)
        result = converter.convert_content(
            a3m_contents={'A': CHAIN_A_A3M, 'B': CHAIN_B_A3M}
        )
        
        assert result.num_pairs == 2
        
    def test_query_sequences_extracted(self):
        """Test that query sequences are correctly extracted."""
        converter = A3MToCSVConverter()
        result = converter.convert_content(
            a3m_contents={'A': CHAIN_A_A3M, 'B': CHAIN_B_A3M}
        )
        
        assert 'A' in result.query_sequences
        assert 'B' in result.query_sequences
        assert len(result.query_sequences['A']) == 65  # Actual length
        assert len(result.query_sequences['B']) == 63


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_convert_a3m_to_multimer_csv(self, tmp_path):
        """Test the main convenience function."""
        # Create temp A3M files
        chain_a_file = tmp_path / "chain_A.a3m"
        chain_b_file = tmp_path / "chain_B.a3m"
        chain_a_file.write_text(CHAIN_A_A3M)
        chain_b_file.write_text(CHAIN_B_A3M)
        
        output_file = tmp_path / "paired.csv"
        
        result = convert_a3m_to_multimer_csv(
            a3m_files={'A': chain_a_file, 'B': chain_b_file},
            output_path=output_file
        )
        
        assert result.num_pairs == 4
        assert output_file.exists()
        
    def test_convert_with_include_unpaired(self, tmp_path):
        """Test conversion with include_unpaired=True."""
        chain_a_file = tmp_path / "chain_A.a3m"
        chain_b_file = tmp_path / "chain_B.a3m"
        chain_a_file.write_text(CHAIN_A_A3M)
        chain_b_file.write_text(CHAIN_B_A3M)
        
        result = convert_a3m_to_multimer_csv(
            a3m_files={'A': chain_a_file, 'B': chain_b_file},
            include_unpaired=True
        )
        
        # With unpaired, we should have more rows
        lines = result.csv_per_chain['A'].strip().split('\n')
        assert len(lines) > 5  # More than header + 4 paired
        
    def test_create_paired_msa_per_chain(self, tmp_path):
        """Test creating MSA data structures for Boltz2."""
        chain_a_file = tmp_path / "chain_A.a3m"
        chain_b_file = tmp_path / "chain_B.a3m"
        chain_a_file.write_text(CHAIN_A_A3M)
        chain_b_file.write_text(CHAIN_B_A3M)
        
        result = convert_a3m_to_multimer_csv(
            a3m_files={'A': chain_a_file, 'B': chain_b_file}
        )
        
        msa_per_chain = create_paired_msa_per_chain(result)
        
        assert 'A' in msa_per_chain
        assert 'B' in msa_per_chain
        assert 'paired' in msa_per_chain['A']
        assert 'csv' in msa_per_chain['A']['paired']


class TestAutoDetection:
    """Tests for auto-detection of pairing mode."""
    
    def test_auto_detect_taxid_mode(self, tmp_path):
        """Test auto-detection when TaxIDs are present."""
        chain_a_file = tmp_path / "chain_A.a3m"
        chain_b_file = tmp_path / "chain_B.a3m"
        chain_a_file.write_text(CHAIN_A_TAXID_A3M)
        chain_b_file.write_text(CHAIN_B_TAXID_A3M)
        
        # With use_tax_id=None, should auto-detect
        result = convert_a3m_to_multimer_csv(
            a3m_files={'A': chain_a_file, 'B': chain_b_file},
            use_tax_id=None  # Auto-detect
        )
        
        # Should successfully create pairs
        assert result.num_pairs >= 1
        
    def test_force_taxid_mode(self, tmp_path):
        """Test forcing TaxID mode."""
        chain_a_file = tmp_path / "chain_A.a3m"
        chain_b_file = tmp_path / "chain_B.a3m"
        chain_a_file.write_text(CHAIN_A_TAXID_A3M)
        chain_b_file.write_text(CHAIN_B_TAXID_A3M)
        
        result = convert_a3m_to_multimer_csv(
            a3m_files={'A': chain_a_file, 'B': chain_b_file},
            use_tax_id=True
        )
        
        assert result.num_pairs >= 1
        
    def test_force_uniref_mode(self, tmp_path):
        """Test forcing UniRef mode."""
        chain_a_file = tmp_path / "chain_A.a3m"
        chain_b_file = tmp_path / "chain_B.a3m"
        chain_a_file.write_text(CHAIN_A_A3M)
        chain_b_file.write_text(CHAIN_B_A3M)
        
        result = convert_a3m_to_multimer_csv(
            a3m_files={'A': chain_a_file, 'B': chain_b_file},
            use_tax_id=False
        )
        
        assert result.num_pairs == 4


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_a3m(self):
        """Test handling of empty A3M content."""
        converter = A3MToCSVConverter()
        
        empty_a3m = ""
        msa = A3MParser.parse(empty_a3m)
        assert len(msa.sequences) == 0
        
    def test_single_sequence_a3m(self):
        """Test A3M with only query sequence."""
        single_a3m = """>Query
MKTVRQERL
"""
        msa = A3MParser.parse(single_a3m)
        assert len(msa.sequences) == 1
        
    def test_no_common_organisms(self):
        """Test when chains have no common organisms."""
        chain_a = """>Query
MKTVRQERL
>UniRef100_OnlyInA
MKTVRQERL
"""
        chain_b = """>Query
MVTPEGNVS
>UniRef100_OnlyInB
MVTPEGNVS
"""
        converter = A3MToCSVConverter()
        result = converter.convert_content(
            a3m_contents={'A': chain_a, 'B': chain_b}
        )
        
        # Should only have query pair
        assert result.num_pairs == 1
        
    def test_no_common_with_include_unpaired(self):
        """Test including unpaired when there are no common organisms."""
        chain_a = """>Query
MKTVRQERL
>UniRef100_OnlyInA
MKTVRQERL
"""
        chain_b = """>Query
MVTPEGNVS
>UniRef100_OnlyInB
MVTPEGNVS
"""
        converter = A3MToCSVConverter(include_unpaired=True)
        result = converter.convert_content(
            a3m_contents={'A': chain_a, 'B': chain_b}
        )
        
        # Should have query pair + 2 unpaired
        lines_a = result.csv_per_chain['A'].strip().split('\n')
        assert len(lines_a) == 4  # header + query + 2 unpaired
        
    def test_three_chains(self):
        """Test with three chains."""
        chain_a = """>Query
MKTVRQERL
>UniRef100_Common
MKTVRQERL
"""
        chain_b = """>Query
MVTPEGNVS
>UniRef100_Common
MVTPEGNVS
"""
        chain_c = """>Query
MAAAAEEEE
>UniRef100_Common
MAAAAEEEE
"""
        # Use UniRef-based pairing for test data without TaxIDs
        strategy = GreedyPairingStrategy(use_tax_id=False)
        converter = A3MToCSVConverter(pairing_strategy=strategy)
        result = converter.convert_content(
            a3m_contents={'A': chain_a, 'B': chain_b, 'C': chain_c}
        )
        
        assert len(result.chain_ids) == 3
        assert result.num_pairs == 2  # Query + Common


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
