# MSA-Search NIM

[MSA-Search](https://docs.nvidia.com/nim/bionemo/msa-search/latest/overview.html) Multiple Sequence Alignment (MSA) compares a query amino acid sequence to protein databases, aligning similar sequences to identify conserved regions despite differences in length or motifs. The resulting alignments enhance structural prediction models like AlphaFold2 and OpenFold by leveraging the structural similarity of homologous sequences.

## Getting Started

1) **Generate an `API_KEY`** <BR>
   Visit [https://build.nvidia.com](https://build.nvidia.com) to create your `API_KEY`.
2) **Run the Tutorial Notebooks** <BR>
   a) [MSA-Search](OpenFold2_MSA_Predict_Target_Protein_Structure.ipynb)
   b) [Processing MSA-Search JSON file into an A3M file](OpenFold2_Predict_Target_Protein_Structure.ipynb)
   c) [MSA-Search](OpenFold2_MSA_Predict_Target_Protein_Structure.ipynb)

<P>

## Example Amino Acid Sequence

**[4WQP_1](https://www.rcsb.org/structure/4WQP) | Chain A | Nuclear receptor ROR-gamma | Homo sapiens (9606)**

`MHHHHHHGENLYFQGSAPYASLTEIEHLVQSVCKSYRETCQLRLEDLLRQRSNIFSREEVTGYQRKSMWEMWERCAHHLTEAIQYVVEFAKRLSGFMELCQNDQIVLLKAGAMEVVLVRMCRAYNADNRTVFFEGKYGGMELFRALGCSELISSIFDFSHSLSALHFSEDEIALYTALVLINAHRPGLQEKRKVEQLQYNLELAFHHHLCKTHRQSILAKLPPKGKLRSLCSQHVERLQIFQHLHPIVVQAAFPPLYKELFSGNS`

<P>

## References

**MMseqs2** Kallenborn, F.; *et al.* "[GPU-Accelerated Homology Search with MMseqs2.](https://www.biorxiv.org/content/10.1101/2024.11.13.623350v6)" *bioRxiv* **2024**. 

**RORc Antagonists** Rene, O.; *et al*. "[Minor Structural Change to Tertiary Sulfonamide RORc Ligands Led to Opposite Mechanisms of Action.](https://pubs.acs.org/doi/10.1021/ml500420y)" *ACS Med. Chem. Lett.* **2015**, *6*, 276-281.

<P>
