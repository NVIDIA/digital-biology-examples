# Release Notes - v0.3.0

## 🎉 Major Features

### GPU-Accelerated MSA Search Integration
- Full integration with NVIDIA MSA Search NIM
- Support for A3M, FASTA, and Stockholm formats
- Batch MSA search capabilities
- Available databases: Uniref30_2302, colabfold_envdb_202108, PDB70_220313

### New API Methods
- `configure_msa_search()` - Configure MSA Search NIM endpoint
- `search_msa()` - Standalone MSA search
- `predict_with_msa_search()` - Combined MSA + structure prediction
- `predict_ligand_with_msa_search()` - MSA + ligand + affinity prediction
- `batch_msa_search()` - Process multiple sequences

### Enhanced CLI Commands
- `boltz2 msa-search` - Search and save MSA alignments
- `boltz2 msa-predict` - Combined MSA search + structure prediction
- `boltz2 msa-ligand` - MSA-guided ligand affinity prediction

### Multi-Endpoint Improvements
- Added `get_health_status()` method
- Added `get_healthy_endpoints()` method
- Improved health monitoring

## 🐛 Bug Fixes
- Fixed batch MSA search parameter requirements
- Corrected database names in all examples
- Fixed CLI multi-endpoint syntax
- Updated all documentation for consistency

## 📚 Documentation
- New MSA Search Guide with comprehensive examples
- Updated Affinity Prediction Guide with MSA sections
- New example scripts for MSA integration
- Corrected database names throughout

## 🔧 Technical Details
- Compatible with MSA Search NIM endpoints
- Supports both local and NVIDIA-hosted deployments
- Async/await support for all MSA operations
- Comprehensive error handling and retry logic
