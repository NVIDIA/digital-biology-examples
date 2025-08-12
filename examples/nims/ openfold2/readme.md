# Predict Target Protein Structure with OpenFold2 and OpenFold2 + MSA-Search

[MSA-Search](https://docs.nvidia.com/nim/bionemo/msa-search/latest/overview.html) Multiple Sequence Alignment (MSA) compares a query amino acid sequence to protein databases, aligning similar sequences to identify conserved regions despite differences in length or motifs. The resulting alignments enhance structural prediction models like AlphaFold2 and OpenFold by leveraging the structural similarity of homologous sequences.

[OpenFold2](https://docs.nvidia.com/nim/bionemo/openfold2/latest/overview.html) is a protein structure prediction model from the [OpenFold Consortium](https://openfold.io/) and the [Alquraishi Laboratory](https://www.aqlab.io/). The model is a PyTorch re-implementation of Google Deepmind’s [AlphaFold2](https://github.com/google-deepmind/alphafold), with support for both training and inference. OpenFold2 demonstrates parity accuracy with AlphaFold2, and improved speed, see the project home for more detail [github.com/aqlaboratory/openfold](https://github.com/aqlaboratory/openfold).

