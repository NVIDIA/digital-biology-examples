#!/usr/bin/env python3
"""
11_msa_search_large_protein.py

Demonstrates MSA Search NIM integration with Boltz-2 for a large (~500 residue) protein.
This example uses Human Serum Albumin (HSA) to showcase the benefits of MSA-guided 
structure prediction for larger proteins.

Key Features:
- MSA search for large proteins
- Performance comparison with/without MSA
- Different MSA parameter exploration
- Multiple format exports
"""

import asyncio
import time
from pathlib import Path
from boltz2_client import Boltz2Client

# Human Serum Albumin Domain I-III (PDB: 1AO6 extended)
# ~500 residues - a blood plasma protein that binds various molecules
HSA_SEQUENCE = """
DAHKSEVAHRFKDLGEENFKALVLIAFAQYLQQCPFEDHVKLVNEVTEFAKTCVADESAENCDKSLHTLFGDKLCTVATLR
ETYGEMADCCAKQEPERNECFLQHKDDNPNLPRLVRPEVDVMCTAFHDNEETFLKKYLYEIARRHPYFYAPELLFFAKRYK
AAFTECCQAADKAACLLPKLDELRDEGKASSAKQRLKCASLQKFGERAFKAWAVARLSQRFPKAEFAEVSKLVTDLTKVHT
ECCHGDLLECADDRADLAKYICENQDSISSKLKECCEKPLLEKSHCIAEVENDEMPADLPSLAADFVESKDVCKNYAEAKD
VFLGMFLYEYARRHPDYSVVLLLRLAKTYETTLEKCCAAADPHECYAKVFDEFKPLVEEPQNLIKQNCELFEQLGEYKFQN
ALLVRYTKKVPQVSTPTLVEVSRNLGKVGSKCCKHPEAKRMPCAEDYLSVVLNQLCVLHEKTPVSDRVTKCCTESLVNRRP
CFSALEVDETYVPKEFNAETFTFHADICTLSEKERQIKKQTALVELVKHKPKATKEQLKAVMDDFAAFVEKCCKADDKETC
""".replace("\n", "")


async def analyze_msa_search_results(response):
    """Analyze MSA search response."""
    total_sequences = 0
    databases_info = []
    
    for db_name, formats in response.alignments.items():
        for fmt, record in formats.items():
            seq_count = record.alignment.count('\n>')
            total_sequences += seq_count
            databases_info.append({
                'database': db_name,
                'format': fmt,
                'sequences': seq_count
            })
    
    return total_sequences, databases_info


async def test_structure_prediction_without_msa(client: Boltz2Client, sequence: str, output_dir: Path):
    """Predict structure without MSA."""
    print("\n🔬 BASELINE: Structure Prediction WITHOUT MSA")
    print("=" * 60)
    
    start_time = time.time()
    
    result = await client.predict_protein_structure(
        sequence=sequence,
        recycling_steps=3,
        sampling_steps=50,
        diffusion_samples=1
    )
    
    elapsed_time = time.time() - start_time
    confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
    
    # Save structure
    output_path = output_dir / "hsa_no_msa.cif"
    output_path.write_text(result.structures[0].structure)
    
    print(f"✅ Completed in {elapsed_time:.1f} seconds")
    print(f"📊 Confidence score: {confidence:.3f}")
    print(f"💾 Structure saved to: {output_path}")
    
    return {
        'time': elapsed_time,
        'confidence': confidence,
        'path': output_path
    }


async def test_msa_search_only(client: Boltz2Client, sequence: str, output_dir: Path):
    """Perform MSA search and analyze results."""
    print("\n🔍 MSA SEARCH ANALYSIS")
    print("=" * 60)
    
    start_time = time.time()
    
    # Search MSA
    response = await client.search_msa(
        sequence=sequence,
        databases=["all"],
        max_msa_sequences=1000,
        e_value=0.001
    )
    
    search_time = time.time() - start_time
    
    # Analyze results
    total_seqs, db_info = await analyze_msa_search_results(response)
    
    print(f"✅ MSA search completed in {search_time:.1f} seconds")
    print(f"📊 MSA Statistics:")
    print(f"   Total sequences found: {total_seqs}")
    print(f"   Databases searched: {len(response.alignments)}")
    
    print("\n📚 Database breakdown:")
    for info in db_info:
        print(f"   - {info['database']}: {info['sequences']} sequences ({info['format']} format)")
    
    # Save MSA in A3M format
    msa_path = output_dir / "hsa_msa.a3m"
    msa_path = await client.search_msa(
        sequence=sequence,
        databases=["all"],
        max_msa_sequences=1000,
        e_value=0.001,
        output_format="a3m",
        save_path=msa_path
    )
    
    print(f"\n💾 MSA saved to: {msa_path}")
    print(f"📏 File size: {msa_path.stat().st_size / 1024:.1f} KB")
    
    return {
        'time': search_time,
        'total_sequences': total_seqs,
        'path': msa_path
    }


async def test_structure_prediction_with_msa(client: Boltz2Client, sequence: str, output_dir: Path):
    """Predict structure with MSA search."""
    print("\n🔬 ENHANCED: Structure Prediction WITH MSA")
    print("=" * 60)
    
    start_time = time.time()
    
    result = await client.predict_with_msa_search(
        sequence=sequence,
        polymer_id="A",
        databases=["all"],
        max_msa_sequences=1000,
        e_value=0.001,
        recycling_steps=3,
        sampling_steps=50,
        diffusion_samples=1
    )
    
    elapsed_time = time.time() - start_time
    confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
    
    # Save structure
    output_path = output_dir / "hsa_with_msa.cif"
    output_path.write_text(result.structures[0].structure)
    
    print(f"✅ Completed in {elapsed_time:.1f} seconds")
    print(f"📊 Confidence score: {confidence:.3f}")
    print(f"💾 Structure saved to: {output_path}")
    
    return {
        'time': elapsed_time,
        'confidence': confidence,
        'path': output_path
    }


async def test_different_msa_parameters(client: Boltz2Client, sequence: str, output_dir: Path):
    """Test different MSA parameters."""
    print("\n🧪 PARAMETER EXPLORATION: Different MSA Sizes")
    print("=" * 60)
    
    # Test with first 200 residues for faster results
    test_sequence = sequence[:200]
    
    msa_configs = [
        {'max_seqs': 100, 'e_value': 0.01, 'name': 'small_lenient'},
        {'max_seqs': 500, 'e_value': 0.001, 'name': 'medium_standard'},
        {'max_seqs': 1000, 'e_value': 0.0001, 'name': 'large_strict'}
    ]
    
    results = []
    
    for config in msa_configs:
        print(f"\n📊 Testing: {config['name']} (max_seqs={config['max_seqs']}, e_value={config['e_value']})")
        
        try:
            start_time = time.time()
            
            result = await client.predict_with_msa_search(
                sequence=test_sequence,
                polymer_id="A",
                databases=["all"],
                max_msa_sequences=config['max_seqs'],
                e_value=config['e_value'],
                recycling_steps=3,
                sampling_steps=50
            )
            
            elapsed_time = time.time() - start_time
            confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
            
            results.append({
                'config': config['name'],
                'max_sequences': config['max_seqs'],
                'e_value': config['e_value'],
                'time': elapsed_time,
                'confidence': confidence
            })
            
            print(f"   ✅ Confidence: {confidence:.3f} | Time: {elapsed_time:.1f}s")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    # Summary table
    if results:
        print("\n📊 Parameter Comparison Summary")
        print("=" * 70)
        print(f"{'Config':<20} {'Max Seqs':<10} {'E-value':<10} {'Confidence':<12} {'Time (s)':<10}")
        print("-" * 70)
        for r in results:
            print(f"{r['config']:<20} {r['max_sequences']:<10} {r['e_value']:<10.4f} {r['confidence']:<12.3f} {r['time']:<10.1f}")
    
    return results


async def test_format_exports(client: Boltz2Client, sequence: str, output_dir: Path):
    """Test exporting MSA in different formats."""
    print("\n📁 FORMAT EXPORT TEST")
    print("=" * 60)
    
    # Use first 150 residues for quick testing
    test_sequence = sequence[:150]
    
    formats = ["a3m", "fasta"]  # "sto" has issues with the current API
    export_results = {}
    
    for fmt in formats:
        print(f"\n📄 Exporting as {fmt.upper()}...")
        
        try:
            output_path = output_dir / f"hsa_export.{fmt}"
            
            path = await client.search_msa(
                sequence=test_sequence,
                databases=["all"],
                max_msa_sequences=50,
                e_value=0.001,
                output_format=fmt,
                save_path=output_path
            )
            
            file_size = path.stat().st_size
            
            # Read first few lines
            content = path.read_text()
            lines = content.split('\n')[:5]
            
            export_results[fmt] = {
                'path': path,
                'size': file_size,
                'preview': lines
            }
            
            print(f"   ✅ Saved to: {path}")
            print(f"   📏 Size: {file_size:,} bytes")
            print(f"   📝 Preview:")
            for line in lines:
                if line and len(line) > 80:
                    print(f"      {line[:77]}...")
                elif line:
                    print(f"      {line}")
                    
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    return export_results


async def main():
    """Main execution function."""
    print("🧬 MSA Search Demo: Large Protein (~500 residues)")
    print("=" * 70)
    print(f"\n📊 Protein: Human Serum Albumin (HSA)")
    print(f"📏 Length: {len(HSA_SEQUENCE)} residues")
    print(f"🔤 Sequence preview: {HSA_SEQUENCE[:50]}...")
    
    # Create output directory
    output_dir = Path("msa_search_large_protein_results")
    output_dir.mkdir(exist_ok=True)
    print(f"\n📁 Output directory: {output_dir}")
    
    # Initialize client
    client = Boltz2Client(base_url="http://localhost:8000")
    
    try:
        # Check connectivity
        health = await client.health_check()
        print(f"\n✅ Boltz-2 server status: {health.status}")
        
        # Configure MSA Search
        client.configure_msa_search(
            msa_endpoint_url="http://your-msa-nim:8000",
            timeout=600,  # 10 minutes for large proteins
            max_retries=3
        )
        print("✅ MSA Search configured")
        
        # Run tests
        results = {}
        
        # 1. Baseline without MSA
        results['no_msa'] = await test_structure_prediction_without_msa(
            client, HSA_SEQUENCE, output_dir
        )
        
        # 2. MSA search analysis
        results['msa_search'] = await test_msa_search_only(
            client, HSA_SEQUENCE, output_dir
        )
        
        # 3. Prediction with MSA
        results['with_msa'] = await test_structure_prediction_with_msa(
            client, HSA_SEQUENCE, output_dir
        )
        
        # 4. Parameter exploration
        results['parameters'] = await test_different_msa_parameters(
            client, HSA_SEQUENCE, output_dir
        )
        
        # 5. Format exports
        results['formats'] = await test_format_exports(
            client, HSA_SEQUENCE, output_dir
        )
        
        # Final summary
        print("\n" + "=" * 70)
        print("🎉 FINAL SUMMARY")
        print("=" * 70)
        
        print("\n📊 Performance Comparison:")
        print(f"{'Method':<25} {'Confidence':<12} {'Time (s)':<10} {'Notes':<30}")
        print("-" * 77)
        
        # Without MSA
        print(f"{'Without MSA':<25} {results['no_msa']['confidence']:<12.3f} {results['no_msa']['time']:<10.1f} {'Baseline':<30}")
        
        # With MSA
        msa_note = f"{results['msa_search']['total_sequences']} sequences found"
        print(f"{'With MSA (1000 seqs)':<25} {results['with_msa']['confidence']:<12.3f} {results['with_msa']['time']:<10.1f} {msa_note:<30}")
        
        # Calculate improvements
        conf_change = ((results['with_msa']['confidence'] - results['no_msa']['confidence']) / results['no_msa']['confidence']) * 100
        time_increase = ((results['with_msa']['time'] - results['no_msa']['time']) / results['no_msa']['time']) * 100
        
        print("\n📈 Analysis:")
        if conf_change > 0:
            print(f"   🎯 MSA improved confidence by {conf_change:.1f}%")
        else:
            print(f"   📉 Confidence changed by {conf_change:.1f}% with MSA")
        
        print(f"   ⏱️  MSA search increased total time by {time_increase:.0f}%")
        print(f"   📚 MSA search alone took {results['msa_search']['time']:.1f} seconds")
        
        print(f"\n💾 All results saved in: {output_dir.absolute()}")
        
        print("\n💡 Key Insights:")
        print("   1. MSA search adds significant time but can improve confidence")
        print("   2. Larger MSA sizes generally improve results but with diminishing returns")
        print("   3. E-value threshold affects both quality and search time")
        print("   4. For well-studied proteins, MSA impact may be modest")
        
        print("\n🔬 Next Steps:")
        print("   1. Visualize structures in PyMOL/ChimeraX")
        print("   2. Compare with experimental structure (PDB: 1AO6)")
        print("   3. Try with less well-studied proteins for bigger MSA impact")
        print("   4. Experiment with specific database selections")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
