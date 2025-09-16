#!/usr/bin/env python3
"""
Simple MSA Search Demo

Demonstrates MSA Search NIM functionality with a protein sequence.
This example focuses on the MSA search capabilities without structure prediction.
"""

import asyncio
import time
from pathlib import Path
from boltz2_client import Boltz2Client, MSAFormatConverter

# Test protein: Human Carbonic Anhydrase II (260 residues)
# A well-studied enzyme that catalyzes CO2 hydration
CA2_SEQUENCE = """
SHHWGYGKHNGPEHWHKDFPIAKGERQSPVDIDTHTAKYDPSLKPLSVSYDQATSLRILNNGHAFNVEFDDSQDKAVLKGGP
LDGTYRLIQFHFHWGSLDGQGSEHTVDKKKYAAELHLVHWNTKYGDFGKAVQQPDGLAVLGIFLKVGSAKPGLQKVVDVLDS
IKTKGKSADFTNFDPRGLLPESLDYWTYPGSLTTPPLLECVTWIVLKEPISVSSEQVLKFRKLNFNGEGEPEELMVDNWRPY
DQGSSVPAFKQ
""".replace("\n", "")


async def demonstrate_msa_search():
    """Demonstrate MSA search functionality."""
    print("🧬 MSA Search NIM Demonstration")
    print("=" * 60)
    print(f"\n📊 Test Protein: Human Carbonic Anhydrase II")
    print(f"📏 Length: {len(CA2_SEQUENCE)} residues")
    print(f"🔤 Sequence: {CA2_SEQUENCE[:50]}...")
    
    # Create output directory
    output_dir = Path("msa_search_demo_results")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize client
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Configure MSA Search
    print("\n⚙️  Configuring MSA Search NIM...")
    client.configure_msa_search(
        msa_endpoint_url="http://localhost:8000",
        timeout=300
    )
    print("✅ MSA Search configured")
    
    # Test 1: Basic MSA Search
    print("\n" + "="*60)
    print("TEST 1: Basic MSA Search")
    print("="*60)
    
    start_time = time.time()
    response = await client.search_msa(
        sequence=CA2_SEQUENCE,
        databases=["all"],
        max_msa_sequences=500,
        e_value=0.001
    )
    search_time = time.time() - start_time
    
    print(f"\n✅ MSA search completed in {search_time:.1f} seconds")
    print(f"📊 Results:")
    
    # Analyze alignments
    total_sequences = 0
    for db_name, formats in response.alignments.items():
        print(f"\n   Database: {db_name}")
        for fmt, record in formats.items():
            seq_count = record.alignment.count('\n>')
            total_sequences += seq_count
            print(f"     Format: {fmt} | Sequences: {seq_count}")
            
            # Show first sequence
            lines = record.alignment.split('\n')
            for i, line in enumerate(lines[:4]):
                if line.startswith('>'):
                    print(f"     First hit: {line[:70]}...")
                    break
    
    print(f"\n   Total sequences across all databases: {total_sequences}")
    
    # Test 2: Save MSA in Different Formats
    print("\n" + "="*60)
    print("TEST 2: Export MSA in Different Formats")
    print("="*60)
    
    formats = ["a3m", "fasta"]
    
    for fmt in formats:
        print(f"\n📄 Exporting as {fmt.upper()}...")
        
        try:
            output_path = output_dir / f"ca2_msa.{fmt}"
            path = await client.search_msa(
                sequence=CA2_SEQUENCE,
                databases=["all"],
                max_msa_sequences=100,  # Fewer for quick export
                e_value=0.001,
                output_format=fmt,
                save_path=output_path
            )
            
            file_size = path.stat().st_size
            print(f"   ✅ Saved to: {path}")
            print(f"   📏 File size: {file_size:,} bytes")
            
            # Show preview
            content = path.read_text()
            lines = content.split('\n')[:5]
            print(f"   📝 Preview:")
            for line in lines:
                if line and len(line) > 70:
                    print(f"      {line[:67]}...")
                elif line:
                    print(f"      {line}")
                    
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    # Test 3: Different Database Selections
    print("\n" + "="*60)
    print("TEST 3: Different Database Selections")
    print("="*60)
    
    # Test with specific databases
    test_configs = [
        {"databases": ["Uniref30_2302"], "name": "UniRef30 only"},
        {"databases": ["PDB70_220313"], "name": "PDB70 only"},
        {"databases": ["all"], "name": "All databases"}
    ]
    
    for config in test_configs[:2]:  # Just test first two for speed
        print(f"\n🔍 Searching {config['name']}...")
        
        try:
            start_time = time.time()
            response = await client.search_msa(
                sequence=CA2_SEQUENCE[:100],  # Shorter sequence for speed
                databases=config["databases"],
                max_msa_sequences=50,
                e_value=0.01
            )
            search_time = time.time() - start_time
            
            # Count results
            total = 0
            for db_name, formats in response.alignments.items():
                for fmt, record in formats.items():
                    seq_count = record.alignment.count('\n>')
                    total += seq_count
            
            print(f"   ✅ Found {total} sequences in {search_time:.1f}s")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    # Test 4: Parameter Effects
    print("\n" + "="*60)
    print("TEST 4: E-value Parameter Effects")
    print("="*60)
    
    e_values = [1.0, 0.1, 0.01, 0.001]
    
    print(f"\n{'E-value':<10} {'Sequences':<15} {'Time (s)':<10}")
    print("-" * 35)
    
    for e_val in e_values:
        try:
            start_time = time.time()
            response = await client.search_msa(
                sequence=CA2_SEQUENCE[:150],  # Use partial sequence
                databases=["all"],
                max_msa_sequences=100,
                e_value=e_val
            )
            search_time = time.time() - start_time
            
            # Count sequences
            total = 0
            for db_name, formats in response.alignments.items():
                for fmt, record in formats.items():
                    total += record.alignment.count('\n>')
            
            print(f"{e_val:<10.3f} {total:<15} {search_time:<10.1f}")
            
        except Exception as e:
            print(f"{e_val:<10.3f} {'Error':<15} {'-':<10}")
    
    # Summary
    print("\n" + "="*60)
    print("🎉 MSA Search Demo Complete!")
    print("="*60)
    print(f"\n📁 Results saved in: {output_dir.absolute()}")
    print("\n💡 Key Takeaways:")
    print("   1. MSA search typically takes 30-120 seconds")
    print("   2. Multiple databases are searched in parallel")
    print("   3. E-value threshold significantly affects result count")
    print("   4. Results can be exported in multiple formats")
    print("   5. Different databases contain different homologs")


async def main():
    """Main execution."""
    try:
        await demonstrate_msa_search()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
