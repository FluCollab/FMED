# Flu Mutation Effect Database

[![View Database](https://img.shields.io/badge/View-Database-blue)](https://flucollab.github.io/FMED/)
[![Submit Mutation](https://img.shields.io/badge/Submit-Mutation-green)](https://github.com/flucollab/FMED/issues/new?template=mutation_submission.yml)
[![Discussions](https://img.shields.io/badge/Join-Discussions-purple)](https://github.com/flucollab/FMED/discussions)

## Overview

The Flu Mutation Effect Database (FMED) is an innovative GitHub-based system for crowdsourcing influenza mutation data. It leverages GitHub Issues as a submission mechanism, GitHub Actions for automated processing, and GitHub Pages for a public-facing database viewer.

Researchers can submit new mutations identified from scientific publications, including details about the mutation, phenotypic effects, and references to the experimental approach. This approach allows for the creation of a centralized, open-access repository where mutation data is updated, discussed, and refined by contributors worldwide.

## Data Access

The FMED database is open and accessible in multiple formats:

### Web Interface
Browse the [Database Viewer](https://flucollab.github.io/FMED/) to see mutations in Table or Sequence view.

### Static Data Files
*   [parsed_issues.tsv](docs/parsed_issues.tsv): Raw validated mutation data.
*   [validated_dois.tsv](docs/validated_dois.tsv): Enriched data with DOI metadata (Authors, Year, Title, Journal).

### Programmatic API
FMED provides a static JSON API for programmatic access:
*   **All Mutations**: `docs/api/all.json`
*   **By Protein**: `docs/api/protein/{PROTEIN}.json` (e.g., `api/protein/HA.json`)
*   **Reference Sequences**: `docs/api/sequences.json`

---

## 🔬 View the Database

Browse all submitted mutations at: **[FMED Database Viewer](https://flucollab.github.io/FMED/)**

The database can be filtered by protein (HA, NA, PB2, PB1, PA, NP, M1, M2, NS1, NS2) and searched by mutation, effect, or publication.

## 📝 Submit Mutations

### Single Mutation
Use the [Mutation Submission Form](https://github.com/flucollab/FMED/issues/new?template=mutation_submission.yml) to submit a single mutation.

### Bulk Submission
Use the [Bulk Mutation Submission Form](https://github.com/flucollab/FMED/issues/new?template=bulk_mutation_submission.yml) to submit multiple mutations at once using a TSV table.

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed submission guidelines.

## 💬 Discussions

Have questions about specific mutations or the database? Join our [GitHub Discussions](https://github.com/flucollab/FMED/discussions):

- **Mutation Q&A** - Ask questions about specific mutations
- **Data Requests** - Request new mutations to be added
- **General** - General project discussion

## Data Schema

Each mutation entry contains:

| Field | Description |
|-------|-------------|
| Protein | The viral protein (HA, NA, PB2, PB1, PA, NP, M1, M2, NS1, NS2) |
| Mutation | The amino acid change (e.g., K135E) |
| WT Accession | GenBank accession of the wild-type sequence |
| Effect | Phenotypic effect (e.g., Drug resistance, Mammalian adaptation) |
| DOI | Publication DOI supporting the finding |
| Notes | Additional context or details |

## License

See [LICENSE.md](LICENSE.md) for details.
