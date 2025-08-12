# Predict Target Protein Structures with OpenFold2 and OpenFold2 + MSA-Search

[MSA-Search](https://docs.nvidia.com/nim/bionemo/msa-search/latest/overview.html) Multiple Sequence Alignment (MSA) compares a query amino acid sequence to protein databases, aligning similar sequences to identify conserved regions despite differences in length or motifs. The resulting alignments enhance structural prediction models like AlphaFold2 and OpenFold by leveraging the structural similarity of homologous sequences.

[OpenFold2](https://docs.nvidia.com/nim/bionemo/openfold2/latest/overview.html) is a protein structure prediction model from the [OpenFold Consortium](https://openfold.io/) and the [Alquraishi Laboratory](https://www.aqlab.io/). The model is a PyTorch re-implementation of Google Deepmind’s [AlphaFold2](https://github.com/google-deepmind/alphafold), with support for both training and inference. OpenFold2 demonstrates parity accuracy with AlphaFold2, and improved speed, see the project home for more detail [github.com/aqlaboratory/openfold](https://github.com/aqlaboratory/openfold).

<P>

## Getting Started

1) **Generate an `API_KEY`** <BR>
   Visit [https://build.nvidia.com](https://build.nvidia.com) to create your `API_KEY`.

2) **Run the Tutorial Notebooks** <BR>
   [OpenFold2](OpenFold2_MSA_Predict_Target_Protein_Structure.ipynb) or [MSA-Search + OpenFold2](OpenFold2_Predict_Target_Protein_Structure.ipynb)

<P>

## References

**OpenFold2** Ahdritz, G.; *et al*. "[OpenFold: Retraining AlphaFold2 Yields New Insights into its Learning Mechanisms and Capacity for Generalization.](https://www.nature.com/articles/s41592-024-02272-z)" *Nat. Methods* **2024**, *21*, 1514–1524.

**MMseqs2** Kallenborn, F.; *et al.* "[GPU-Accelerated Homology Search with MMseqs2.](https://www.biorxiv.org/content/10.1101/2024.11.13.623350v6)" *bioRxiv* **2024**. 

**RORc Antagonists** Rene, O.; *et al*. "[Minor Structural Change to Tertiary Sulfonamide RORc Ligands Led to Opposite Mechanisms of Action.](https://pubs.acs.org/doi/10.1021/ml500420y)" *ACS Med. Chem. Lett.* **2015**, *6*, 276-281.

<P>
