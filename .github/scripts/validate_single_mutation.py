"""
Validates a single mutation entry from a JSON file.

Returns validation results as JSON and appropriate exit codes.
"""

import sys
import os
import json

from utils import (
    validate_row,
    read_tsv,
    is_duplicate,
    VALID_PROTEINS,
    VALID_EFFECTS
)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"valid": False, "errors": ["Usage: python validate_single_mutation.py <json_file> [existing_tsv]"]}))
        sys.exit(1)
    
    json_file = sys.argv[1]
    existing_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Load JSON data
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(json.dumps({"valid": False, "errors": [f"Error reading JSON: {e}"]}))
        sys.exit(1)
    
    # Handle array format from parse_issue_form.py
    if isinstance(data, list):
        if len(data) == 0:
            print(json.dumps({"valid": False, "errors": ["No mutation data found"]}))
            sys.exit(1)
        data = data[0]
    
    # Normalize keys
    row = {
        'protein': data.get('protein', ''),
        'mutation': data.get('mutation', ''),
        'reference_accession': data.get('reference_accession', ''),
        'effect': data.get('effect', ''),
        'doi': data.get('doi', '') or data.get('source_publication', ''),
        'notes': data.get('notes', '')
    }
    
    # Validate all fields
    is_valid, errors = validate_row(row, validate_doi_online=True)
    
    # Check for duplicates
    is_dup = False
    if is_valid and existing_file and os.path.exists(existing_file):
        existing_data = read_tsv(existing_file)
        entry = {
            'protein': row['protein'],
            'mutation': row['mutation'],
            'effect': row['effect'],
            'source_publication': row['doi']
        }
        is_dup = is_duplicate(entry, existing_data)
        if is_dup:
            errors.append("This mutation already exists in the database")
    
    # Build result
    result = {
        "valid": is_valid and not is_dup,
        "is_duplicate": is_dup,
        "errors": errors,
        "data": row
    }
    
    # Generate markdown report for issue comment
    if not is_valid or is_dup:
        report_lines = ["## ❌ Validation Failed\n"]
        
        if errors:
            report_lines.append("The following issues were found:\n")
            for error in errors:
                report_lines.append(f"- {error}")
        
        report_lines.append("\n### Submitted Data\n")
        report_lines.append(f"- **Protein:** {row['protein']}")
        report_lines.append(f"- **Mutation:** {row['mutation']}")
        report_lines.append(f"- **Effect:** {row['effect']}")
        report_lines.append(f"- **DOI:** {row['doi']}")
        
        report_lines.append("\n<details><summary>📖 Validation Rules</summary>\n")
        report_lines.append(f"- **Protein:** Must be one of: {', '.join(VALID_PROTEINS)}")
        report_lines.append("- **Mutation:** Format `[Letter][Number][Letter]` (e.g., K135E)")
        report_lines.append(f"- **Effect:** Must be one of: {', '.join(VALID_EFFECTS)}")
        report_lines.append("- **DOI:** Must be a valid DOI that exists in CrossRef")
        report_lines.append("</details>")
        
        result["report"] = '\n'.join(report_lines)
    
    # Output JSON result
    print(json.dumps(result, indent=2))
    
    # Exit code
    if is_valid and not is_dup:
        sys.exit(0)  # Success
    elif is_dup:
        sys.exit(2)  # Duplicate
    else:
        sys.exit(1)  # Validation failure


if __name__ == "__main__":
    main()
