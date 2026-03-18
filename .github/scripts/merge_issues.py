"""
Merges mutation data from issue body or TSV attachments into the database.
"""

import sys
import base64
import os

from utils import (
    VALID_PROTEINS,
    REQUIRED_COLUMNS,
    validate_protein,
    validate_doi,
    read_tsv,
    write_tsv,
    is_duplicate
)


def decode_base64(encoded_text):
    """Decodes a Base64-encoded string."""
    try:
        decoded_bytes = base64.b64decode(encoded_text)
        return decoded_bytes.decode("utf-8")
    except Exception as e:
        print(f"❌ Error decoding Base64: {e}")
        sys.exit(1)


def parse_issue_body(issue_body):
    """Parses issue body text into a dictionary while ensuring column order."""
    from utils import normalize_line_endings
    
    issue_body = decode_base64(issue_body)
    # Normalize line endings (CRLF/CR -> LF) for cross-platform compatibility
    issue_body = normalize_line_endings(issue_body)
    issue_data = {}
    issue_lines = issue_body.strip().split("\n")

    mapping = {
        "WT sequence": "reference_accession",
        "Effect": "effect",
        "Publication": "source_publication"
    }

    for line in issue_lines:
        parts = line.split(":", 1)
        if len(parts) == 2:
            key, value = parts[0].strip(), parts[1].strip()

            if key == "Mutation":
                # Split mutation into 'protein' and 'mutation'
                mutation_parts = value.split(":")
                if len(mutation_parts) == 2:
                    issue_data["protein"] = mutation_parts[0]  # e.g., "HA"
                    issue_data["mutation"] = mutation_parts[1]  # e.g., "Q226L"
                else:
                    print(f"❌ Invalid mutation format: {value}")
                    return None
            elif key in mapping:
                issue_data[mapping[key]] = value

    # Ensure all required fields are present
    if set(issue_data.keys()) == set(REQUIRED_COLUMNS):
        return {col: issue_data.get(col, "") for col in REQUIRED_COLUMNS}
    else:
        print("❌ Issue body does not contain all required fields.")
        return None


def merge_issues(existing_file, issue_body, new_data_file=None):
    """Merges issue data into an existing TSV dataset while preserving column order."""
    print(f"Received Arguments:")
    print(f"  - Existing File: {existing_file}")
    print(f"  - Issue Body: {issue_body if issue_body else '(No issue body provided)'}")
    print(f"  - New Data File: {new_data_file if new_data_file else '(No attachment provided)'}")

    existing_data = read_tsv(existing_file)

    # Load new data
    new_data = []
    if new_data_file:
        raw_rows = read_tsv(new_data_file)
        print(f"Loaded {len(raw_rows)} rows from attachment. Validating...")
        
        for row in raw_rows:
            prot = row.get("protein", "").strip()
            doi = row.get("source_publication", "").strip() or row.get("doi", "").strip()
            
            # Validate Protein
            if not validate_protein(prot):
                print(f"❌ Invalid Protein: {prot}")
                sys.exit(1)
            
            # Validate DOI
            if not validate_doi(doi):
                print(f"❌ Invalid DOI: {doi}")
                sys.exit(1)
            
            new_data.append(row)
            
    else:
        parsed_issue = parse_issue_body(issue_body)
        if parsed_issue:
            new_data = [parsed_issue]
        else:
            return

    # Deduplicate by 'protein', 'mutation', and 'source_publication' while keeping the original entry
    unique_entries = {}
    for entry in existing_data + new_data:
        # Normalize keys for comparison
        p = entry["protein"]
        m = entry["mutation"]
        s = entry["source_publication"]
        
        key = (p, m, s)
        if key not in unique_entries:
            unique_entries[key] = entry
        else:
            print(f"Skipping duplicate: {p} {m} {s}")

    merged_data = list(unique_entries.values())
  
    # Save the updated dataset
    write_tsv(existing_file, merged_data)
    print("✅ Merged, deduplicated, and validated DOIs in parsed_issues.tsv!")


if __name__ == "__main__":
    merge_issues(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
