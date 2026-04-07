#!/usr/bin/env python3
"""
Direct Boltz2 NIM API call without using boltz2-python-client.
Tests the 1259 residue complex with high parameters.
"""

import requests
import json
import os
import time
import sys

# NIM endpoint
BASE_URL = os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000")

# Sequences (from FASTA files)
PROTEIN_A = "EAKIIFEVDWQCADHITYAVHVQIRWKAGQMKFHMEDPENNYKCRVEPDVLYNWHDCILDIEPKRNGNNHKDYGVIGRPKVIMCICMPKDHWMHSPRFKFIVVKWQWPNIFTSDCEFGQYDPPYRTKVAEVKMELQGRAKTGTELTYHFNGVTAYMSAENLICIWDDSDVFFSVGKTYQHVHLPNRTREIIDMAWVIWIADCIDCMDTIKSHVFWWSISQHEEQNQQRCECPMEIHHVRFQGKRIDRVECVADIGQSSHPCGPAPKRLQVSFHLHCWVCMCCWSTTGCTDGDYDIPEWIWYCYDQWWTMKHMIKPFLRMDARYWEDVHTKFNDINLGRVLYTAVLEFKEEVFKLYHMHKTSKCDQKCAMFKGRVQVAEDFVCNWVFQFCLNCNHIENVQYFIGGQAGMQIKGEPCSIHRNLIIAHPMKDKNTPVMAEKGWKCEYQNMQYTEPWHKCQATVHNQDMYMELTLQMPLVFHQPGYWLPVALLHQWYMRRRHTSGDLTYMDILIHFACISYDRQWHPSPIFAEQIGTRCVIERFRTVYMRYTQVRGSRKIKTSIKRDLIKMMVDFFIPFHDQQMVRQCHQPWAWPSANLPQVVYISIKQSAPMPGRFYVAPWWADQFRGCKPMHRMMPKQKDSAVCNIDCAIHAYFIFSEWHRKNGYYEGLEWALWPPHDWIELYEWCNVQNDTMAQSEQNRFQGTKYVSRQWKMIDKRIRWYPMASMGSHNKMKYKVATHDIQSVISSRADLIPILWNSVTNQVMNRKLKIEHMEVGHHSKWTYLEHLINGLAVFKCCVLFSEAWLSSRMGCKSEDPSDWCFFWLDIEVQYYYITPRRLWQLWYCYEHHKDGIGVDGAQRYSLCILLRDIKWHQEVIFKFDCGLYWLRERLPKTVSRDYCQMYKADIW"

PROTEIN_B = "CLFRNERYSYATQWNYVQPGCEEPFEGTSFPYTKWGPDCWCGCGLKDTYEWCEYRMMTRGFDMCWKNGYDVELSNQCSQYDNFDFWLEVQRWCFAEEFAMEVSKRMPDCDHPHWPKYWQMPNCGVGHCILINHHPPICRTCEAAVYTTTEWNKIFRPFIAEIEWYQHPQEAGPEMMKVFVWFIHICDKSKDSMFMIAHSFLWRLSRLVSVYQQTWDHYFYAEDIHHYTCKGSRQLDMRRKSFEMNMNEPRMLHIRGNLQIWLTCGLFFHFGWTHKSPTGKETNFEQLTKEFWTPCPWRRVSVEASSDLEHRDVQSFGNADKMCDVMGANHMEQRCADIEHYHICPCEELADYTI"

print(f"Protein A: {len(PROTEIN_A)} residues")
print(f"Protein B: {len(PROTEIN_B)} residues")
print(f"Total: {len(PROTEIN_A) + len(PROTEIN_B)} residues")
print()

# Get parameters from command line or use defaults
recycling_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 10
diffusion_samples = int(sys.argv[2]) if len(sys.argv) > 2 else 25

print(f"Parameters: recycling_steps={recycling_steps}, diffusion_samples={diffusion_samples}")
print()

# Build the request payload
payload = {
    "polymers": [
        {
            "id": "A",
            "molecule_type": "protein",
            "sequence": PROTEIN_A
        },
        {
            "id": "B",
            "molecule_type": "protein",
            "sequence": PROTEIN_B
        }
    ],
    "recycling_steps": recycling_steps,
    "diffusion_samples": diffusion_samples,
    "sampling_steps": 200
}

# Check server health first
print("Checking server health...")
try:
    health_resp = requests.get(f"{BASE_URL}/v1/health/ready", timeout=10)
    print(f"Server health: {health_resp.text}")
except Exception as e:
    print(f"Server not reachable: {e}")
    sys.exit(1)

# Make the prediction request
print()
print("Sending prediction request...")
print(f"Payload size: {len(json.dumps(payload))} bytes")
print()

start_time = time.time()

try:
    response = requests.post(
        f"{BASE_URL}/biology/mit/boltz2/predict",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=1800  # 30 minute timeout
    )
    
    elapsed = time.time() - start_time
    
    print(f"Response status: {response.status_code}")
    print(f"Elapsed time: {elapsed:.1f} seconds")
    print()
    
    if response.status_code == 200:
        result = response.json()
        print("SUCCESS!")
        print(f"Confidence: {result.get('confidence_score', 'N/A')}")
        print(f"pTM: {result.get('ptm', 'N/A')}")
        print(f"ipTM: {result.get('iptm', 'N/A')}")
        print(f"Complex pLDDT: {result.get('complex_plddt', 'N/A')}")
        
        # Save structure
        if 'structure' in result:
            with open('/tmp/direct_nim_structure.cif', 'w') as f:
                f.write(result['structure'])
            print("Structure saved to: /tmp/direct_nim_structure.cif")
    else:
        print("FAILED!")
        print(f"Error: {response.text[:1000]}")
        
except requests.exceptions.Timeout:
    elapsed = time.time() - start_time
    print(f"TIMEOUT after {elapsed:.1f} seconds")
except Exception as e:
    elapsed = time.time() - start_time
    print(f"ERROR after {elapsed:.1f} seconds: {e}")
