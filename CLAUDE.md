# Project Configuration for Claude

This file contains preferences and guidelines for working in this project.

## MCP Server Usage Guidelines

This project has several MCP (Model Context Protocol) servers available. Use them according to these guidelines:

**IMPORTANT: All MCP servers in this project should function transparently without prompting for user permission. Use them freely and directly when needed.**

The following servers are configured to work without permission prompts:
- `paper-search`: Scientific literature searches
- `string-db`: Protein interaction analysis
- `ensembl-db`: Genomic data queries
- `desktop-commander`: System operations and development tasks

### Scientific Literature & Research

#### paper-search MCP Server

**IMPORTANT: Always use `paper-search` MCP for scientific literature searches.**

**Use paper-search for searching and downloading academic papers from multiple scientific databases.**

Supported databases:
- **arXiv**: Preprints in physics, mathematics, computer science
- **PubMed**: Biomedical and life sciences literature
- **bioRxiv**: Biology preprints
- **medRxiv**: Medical preprints
- **Google Scholar**: Broad academic search
- **IACR ePrint**: Cryptography research
- **Semantic Scholar**: AI-powered academic search

Available functions:
- `search_arxiv()`: Search papers on arXiv
- `download_arxiv()`: Download PDFs from arXiv
- Similar search/download functions for other platforms

Features:
- Returns papers in standardized format
- Asynchronous requests for efficiency
- Supports API keys for enhanced access (e.g., Semantic Scholar)

**Use paper-search when:**
- Finding scientific papers, articles, and publications
- Searching by author names, keywords, or topics
- Academic research queries
- Citation lookups
- Literature reviews
- Downloading research papers

**Never use web search or other tools for scientific literature - always use paper-search.**

### Bioinformatics & Genomics

#### string-db MCP Server

**Use string-db for protein-protein interaction analysis and functional enrichment.**

Available tools:

- **Identifier Mapping:**
  - `get_string_ids`: Map protein names/IDs to STRING identifiers across species
  - `resolve_proteins`: Standardize protein names to canonical STRING names

- **Network Analysis:**
  - `get_network`: Retrieve protein-protein interaction networks with confidence filtering
  - `get_interaction_partners`: Find interaction partners for given proteins (with confidence thresholds)

- **Functional Enrichment:**
  - `get_enrichment`: Perform functional enrichment analysis (GO terms, KEGG pathways, domains)
  - `get_ppi_enrichment`: Test if protein sets have statistically significant interactions

- **Cross-Species Analysis:**
  - `get_homology`: Retrieve protein homology information across species
  - `get_homology_best`: Find best homology matches in target species

- **Utility:**
  - `get_version`: Get current STRING database version

**Supported species (common):**
- Human (9606), Mouse (10090), Rat (10116)
- Fruit fly (7227), C. elegans (6239), Yeast (4932)

**Use string-db when:**
- Analyzing protein interactions and networks
- Performing functional enrichment analysis
- Mapping proteins across species
- Finding interaction partners or homologs
- Testing for PPI enrichment in protein sets

#### ensembl-db MCP Server

**Use ensembl-db for genomic data retrieval and analysis via the Ensembl REST API.**

Available tools (31 endpoints across 11 categories):

- **Gene Lookup:**
  - `lookup_gene_by_symbol`: Find genes by symbol (e.g., BRCA2)
  - `lookup_gene_by_id`: Find genes by Ensembl stable ID

- **Sequence Retrieval:**
  - `get_sequence`: Retrieve DNA/RNA/protein sequences

- **Variant Analysis:**
  - `get_variants_for_region`: Find genetic variants in genomic regions
  - `vep_region`: Predict variant consequences (Variant Effect Predictor)

- **Cross-Species Homology:**
  - `get_homology`: Find homologous genes/proteins across species

- **Phenotype Data:**
  - `get_phenotype_by_gene`: Retrieve phenotype annotations for genes

- **Regulatory Features:**
  - `get_regulatory_features`: Find regulatory elements in genomic regions

- **Overlap Analysis:**
  - `overlap_region`, `overlap_id`, `overlap_translation`: Find overlapping genomic features

- **Cross-References:**
  - `get_xrefs_by_gene`, `get_xrefs_by_symbol`, `get_xrefs_by_name`: External database references

- **Coordinate Mapping:**
  - Tools for mapping between assemblies and genomic/protein coordinates

- **Ontology & Taxonomy:**
  - Search and retrieve ontology terms and taxonomy information

**Use ensembl-db when:**
- Looking up genes by symbol or ID
- Retrieving genomic sequences
- Analyzing genetic variants and their effects
- Finding gene homologs across species
- Exploring phenotype associations
- Identifying regulatory features
- Mapping between genome assemblies

### System Operations

#### desktop-commander MCP Server

**Use desktop-commander for advanced system interaction, terminal control, and development tasks.**

Available capabilities:

- **Terminal Control:**
  - Execute terminal commands with output streaming
  - Run long-running commands in background
  - Manage and kill processes
  - Monitor command output in real-time

- **Filesystem Operations:**
  - Read/write files
  - Create/list directories
  - Move files and directories
  - Search files across filesystem
  - Get file metadata
  - Negative offset reading (like Unix `tail`)

- **Code Editing:**
  - Surgical text replacements in files
  - Full file rewrites
  - Multiple file editing
  - Pattern-based replacements
  - VSCode-ripgrep recursive code/text search

- **Development Environment:**
  - Execute code in memory (Python, Node.js, R)
  - Instant data analysis for CSV/JSON files
  - Interact with development servers and databases

**Use desktop-commander when:**
- Running terminal commands or shell scripts
- Managing processes or background tasks
- Performing filesystem operations
- Editing code or text files
- Searching code across the project
- Executing code snippets for quick analysis
- Interacting with development servers

### General Purpose

- **filesystem**: File operations within the workspace
- **fetch**: Web content fetching for non-scientific content
- **memory**: Persistent memory across conversations

## Project Context

- **Field**: Bioinformatics / Computational Biology
- **Primary Language**: Python
- **Environment**: Devcontainer with pixi package management

## Code Style Preferences

- Follow existing code style in the repository
- Use type hints in Python code
- Include docstrings for functions and classes
- Follow scientific computing best practices

## Citation Format

When adding inline citations to scientific papers, use Author-Year format:
- Up to two authors: (Munch, 2025) or (Munch and Hobolth, 2025)
- Three or more: (Munch et al., 2025)
- Citation labels should be hyperlinks to the paper on the journal website

## Notes

- This project uses MCP servers for enhanced capabilities
- The devcontainer includes pixi for package management
- MCP servers use pixi environments (conda packages + pip when needed)
- PyPI-based servers are installed with pip in the shared pixi environment to ensure Python headers are available
