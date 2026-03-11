# Contributing to FMED

Thank you for your interest in contributing to the Flu Mutation Effect Database! This guide explains how to submit mutations and participate in the project.

## 🧬 Submitting Mutations

### Single Mutation Submission

To submit a single mutation:

1. Go to [Submit a Mutation](https://github.com/centre-for-virus-research/FMED/issues/new?template=mutation_submission.yml)
2. Fill out the form:
   - **Protein**: Select the protein (HA, NA, PB2, PB1, PA, NP, M1, M2, NS1, NS2)
   - **Mutation**: Enter the mutation in format `[WildType][Position][Mutant]` (e.g., `K135E`)
   - **WT Accession**: GenBank accession number of the wild-type sequence
   - **Effect**: Select the phenotypic effect
   - **Publication DOI**: DOI of the supporting publication (e.g., `10.1128/jvi.01234-21`)
   - **Notes**: Any additional context (optional)
3. Submit the issue

The mutation will be automatically validated and added to the database.

### Bulk Mutation Submission

To submit multiple mutations at once:

1. Go to [Bulk Submission](https://github.com/centre-for-virus-research/FMED/issues/new?template=bulk_mutation_submission.yml)
2. Prepare your data as a TSV (tab-separated values) table with this exact header:

```
protein	mutation	reference_accession	effect	doi	notes
```

3. Either:
   - Paste the TSV data directly into the form, OR
   - Attach a `.tsv` or `.txt` file containing the data

**Example:**
```
protein	mutation	reference_accession	effect	doi	notes
HA	K135E	CY123456	Increased binding	10.1128/jvi.01234-21	Found in H5N1
NA	H275Y	CY789012	Drug resistance	10.1038/nature12345	Oseltamivir resistance
```

### Validation

All submissions are automatically validated:
- ✅ DOI is verified against CrossRef
- ✅ Protein must be a valid influenza protein
- ✅ Duplicate entries are detected and skipped

If validation fails, you'll receive a comment on your issue explaining what went wrong.

## 💬 Using Discussions

Use [GitHub Discussions](https://github.com/centre-for-virus-research/FMED/discussions) for:

| Category | When to Use |
|----------|-------------|
| **Mutation Q&A** | Questions about specific mutations, their effects, or experimental context |
| **Data Requests** | Suggest mutations that should be added (if you don't have a DOI yet) |
| **General** | General questions about the project, methodology, or suggestions |

### Issues vs Discussions

- **Use Issues** → When you have a complete mutation entry with a DOI to submit
- **Use Discussions** → When you have questions, want to discuss data, or need help

## 🔍 Reviewing Submissions

Community members can help review submissions by:

1. Checking the original publication for accuracy
2. Commenting on issues with additional context
3. Suggesting related mutations from the same study

## 📋 Effect Categories

When submitting, choose the most appropriate effect:

| Effect | Description |
|--------|-------------|
| Mammalian adaptation | Increases replication or transmission in mammals |
| Increased binding | Enhanced receptor binding affinity |
| Avian adaptation | Adaptation to avian hosts |
| Drug resistance | Resistance to antivirals (e.g., oseltamivir) |
| Antigenic escape | Escape from antibody recognition |
| Other | Effects not covered above (specify in notes) |

## Questions?

If you have any questions, please open a [Discussion](https://github.com/centre-for-virus-research/FMED/discussions) or contact the maintainers.
