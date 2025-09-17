# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2025-09-11

### Added
- **GPU-accelerated MSA Search NIM Integration**:
  - New `MSASearchClient` for direct MSA Search NIM interaction
  - `MSAFormatConverter` for A3M, FASTA, and Stockholm format support
  - `MSASearchIntegration` for Boltz-2 workflow integration
- **New Client Methods**:
  - `configure_msa_search()` - Configure MSA Search NIM endpoint
  - `search_msa()` - Standalone MSA search
  - `predict_with_msa_search()` - Integrated MSA + structure prediction
  - `predict_ligand_with_msa_search()` - MSA + ligand + affinity prediction
  - `batch_msa_search()` - Batch processing for multiple sequences
- **CLI Commands**:
  - `boltz2 msa-search` - Search and save MSA alignments
  - `boltz2 msa-predict` - Combined MSA search + structure prediction
  - `boltz2 msa-ligand` - MSA-guided ligand affinity prediction
  - `--msa-file` option for existing MSA files
- **Examples**:
  - `10_msa_search_integration.py` - Comprehensive MSA integration demo
  - `11_msa_search_large_protein.py` - Large protein optimization
  - `12_msa_affinity_prediction.py` - MSA-guided affinity prediction
- **Documentation**:
  - New MSA Search Guide with complete usage examples
  - Updated Affinity Prediction Guide with MSA-guided section
  - Enhanced README with MSA integration examples

### Fixed
- Parameter naming consistency: `max_hits` → `max_msa_sequences`, `e_value_threshold` → `e_value`
- MSA file handling in `predict_protein_structure()` method
- Documentation inconsistencies and outdated examples

### Improved
- Better error handling for MSA Search API responses
- Retry logic for MSA Search requests
- More comprehensive test coverage

## [0.2.1] - 2025-08-14

### Added
- Complete multi-endpoint support for ALL Boltz2 NIM functionalities:
  - `predict_protein_structure()` with MSA support
  - `predict_protein_ligand_complex()` with affinity prediction
  - `predict_covalent_complex()`
  - `predict_dna_protein_complex()`
  - `predict_with_advanced_parameters()`
  - `predict_from_yaml_config()` and `predict_from_yaml_file()`
- New `msa` parameter in `predict_protein_structure()` for direct MSA input
- Comprehensive demo notebook (`examples/boltz2_comprehensive_demo.ipynb`) with:
  - Single and multi-endpoint examples
  - Both Python API and CLI demonstrations
  - Advanced features and visualization
- `AlignmentFormat` export in `__init__.py`

### Fixed
- MSA support now correctly uses nested dictionary format `{database: {format: AlignmentFileRecord}}`
- CLI multi-endpoint initialization (removed incorrect `is_async` parameter)
- Multi-endpoint client MSA parameter passing
- YAML configuration MSA format handling

### Changed
- Updated README.md examples (removed `is_async=True` from MultiEndpointClient)
- Improved error handling in multi-endpoint operations
- Better organization of test scripts into `test_scripts/` directory

### Documentation
- New comprehensive demo notebook with complete examples
- Updated all guides for consistency
- Added troubleshooting tips for multi-endpoint usage

## [0.2.0] - Previous release
- Initial multi-endpoint support for virtual screening
- Basic affinity prediction features
- Virtual screening capabilities
