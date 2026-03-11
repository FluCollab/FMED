"""
Enriches mutation data with DOI metadata (authors, year, title, journal).
"""

import csv
import sys

from utils import get_doi_metadata, REQUIRED_COLUMNS


# Output columns include enrichment fields
OUTPUT_COLUMNS = REQUIRED_COLUMNS + ['Authors', 'Year', 'Title', 'Journal', 'Reference', 'DOI_URL']


def enrich_mutations(input_file, output_file):
    """
    Reads mutations from input TSV and writes enriched version with DOI metadata.
    
    Args:
        input_file: Path to input TSV with mutations
        output_file: Path to write enriched TSV
    """
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
        reader = csv.reader(infile, delimiter='\t')
        writer = csv.writer(outfile, delimiter='\t')

        # Read and process header
        header = next(reader)
        writer.writerow(OUTPUT_COLUMNS)

        for row in reader:
            # Safe extraction by name
            row_dict = dict(zip(header, row))
            
            protein = row_dict.get('protein', '')
            mutation = row_dict.get('mutation', '')
            accession = row_dict.get('reference_accession', '')
            effect = row_dict.get('effect', '')
            doi = row_dict.get('source_publication', '')
            notes = row_dict.get('notes', '')
            
            # Fetch DOI metadata using shared utility
            metadata = get_doi_metadata(doi, verbose=True)
            
            if metadata:
                authors = metadata['authors']
                year = metadata['year']
                title = metadata['title']
                journal = metadata['journal']
                doi_url = metadata['doi_url']
                reference = f"{authors} ({year}). {title}. {journal}."
            else:
                authors = ''
                year = ''
                title = ''
                journal = ''
                doi_url = 'Error: DOI not found'
                reference = ''
            
            writer.writerow([
                protein, mutation, accession, effect, doi, notes,
                authors, year, title, journal, reference, doi_url
            ])


def main():
    if len(sys.argv) < 2:
        print("Usage: python add_doi_details.py <input_file> [output_file]")
        print("Example: python add_doi_details.py input.tsv output.tsv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "output.tsv"
    
    enrich_mutations(input_file, output_file)
    print(f"✅ Enriched data written to {output_file}")


if __name__ == "__main__":
    main()
