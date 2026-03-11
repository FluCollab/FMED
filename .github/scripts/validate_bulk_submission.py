"""
Validates bulk TSV submissions and generates a validation report.

This script parses bulk mutation submissions from issue bodies, validates each row,
and outputs:
1. A markdown validation report (printed to stdout for use as issue comment)
2. A JSON file with only valid rows (for later merging when accepted)
"""

import sys
import os
import json
import re
import requests

from utils import (
    VALID_PROTEINS,
    VALID_EFFECTS,
    REQUIRED_COLUMNS,
    validate_row,
    validate_doi,
    read_tsv,
    is_duplicate
)


def parse_issue_body(body_text):
    """
    Parses a GitHub Issue Form body (Markdown) into a dictionary.
    """
    data = {}
    lines = body_text.replace('\r\n', '\n').split('\n')
    
    current_key = None
    current_value = []
    
    for line in lines:
        line_stripped = line.strip()
        
        if line_stripped.startswith('### '):
            if current_key:
                val = '\n'.join(current_value).strip()
                if val == "_No response_":
                    val = None
                data[current_key] = val
            
            current_key = line_stripped[4:].strip()
            current_value = []
        elif current_key:
            current_value.append(line)
            
    if current_key:
        val = '\n'.join(current_value).strip()
        if val == "_No response_":
            val = None
        data[current_key] = val
        
    return data


def download_attachment(url):
    """Downloads TSV content from a GitHub attachment URL."""
    headers = {}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        raise Exception(f"Failed to download attachment: HTTP {response.status_code}")
    
    return response.text


def parse_tsv_content(tsv_content):
    """
    Parses TSV content into a list of row dictionaries.
    
    Returns:
        Tuple of (rows, header_error)
        - rows: List of dictionaries with parsed data
        - header_error: Error message if header is invalid, None otherwise
    """
    lines = [line.strip() for line in tsv_content.strip().split('\n') if line.strip()]
    
    if not lines:
        return [], "TSV data is empty"
    
    # Validate header
    header_row = [h.strip().lower() for h in lines[0].split('\t')]
    expected_header = ['protein', 'mutation', 'reference_accession', 'effect', 'doi', 'notes']
    
    if header_row != expected_header:
        return [], f"Invalid header. Expected: {expected_header}, Got: {header_row}"
    
    # Parse data rows
    rows = []
    for i, line in enumerate(lines[1:], start=2):
        parts = line.split('\t')
        
        # Pad with empty strings if needed
        while len(parts) < 6:
            parts.append("")
        
        row = {
            'row_number': i,
            'protein': parts[0].strip(),
            'mutation': parts[1].strip(),
            'reference_accession': parts[2].strip(),
            'effect': parts[3].strip(),
            'doi': parts[4].strip(),
            'notes': parts[5].strip()
        }
        rows.append(row)
    
    return rows, None


def check_duplicates(rows, existing_file):
    """
    Checks for duplicates against existing database.
    
    Returns:
        Dictionary mapping row_number to duplicate status
    """
    duplicates = {}
    
    if os.path.exists(existing_file):
        existing_data = read_tsv(existing_file)
        for row in rows:
            entry = {
                'protein': row['protein'],
                'mutation': row['mutation'],
                'source_publication': row['doi']
            }
            if is_duplicate(entry, existing_data):
                duplicates[row['row_number']] = True
    
    return duplicates


def validate_bulk_submission(tsv_content, existing_file=None):
    """
    Validates all rows in a bulk TSV submission.
    
    Returns:
        Dictionary with validation results:
        {
            'valid_rows': [...],
            'invalid_rows': [...],
            'duplicate_rows': [...],
            'header_error': str or None
        }
    """
    rows, header_error = parse_tsv_content(tsv_content)
    
    if header_error:
        return {
            'valid_rows': [],
            'invalid_rows': [],
            'duplicate_rows': [],
            'header_error': header_error
        }
    
    # Check for duplicates
    duplicates = {}
    if existing_file:
        duplicates = check_duplicates(rows, existing_file)
    
    valid_rows = []
    invalid_rows = []
    duplicate_rows = []
    
    for row in rows:
        row_num = row['row_number']
        
        # Check duplicate first
        if duplicates.get(row_num):
            duplicate_rows.append({**row, 'errors': ['Already exists in database']})
            continue
        
        # Validate row
        is_valid, errors = validate_row(row, validate_doi_online=True)
        
        if is_valid:
            valid_rows.append(row)
        else:
            invalid_rows.append({**row, 'errors': errors})
    
    return {
        'valid_rows': valid_rows,
        'invalid_rows': invalid_rows,
        'duplicate_rows': duplicate_rows,
        'header_error': None
    }


def generate_markdown_report(results):
    """
    Generates a markdown validation report for posting as an issue comment.
    """
    lines = []
    lines.append("## 📋 Bulk Submission Validation Report\n")
    
    # Header error
    if results['header_error']:
        lines.append(f"### ❌ Header Error\n")
        lines.append(f"**{results['header_error']}**\n")
        lines.append("Please ensure your TSV has the header: `protein\tmutation\treference_accession\teffect\tdoi\tnotes`\n")
        return '\n'.join(lines)
    
    valid = results['valid_rows']
    invalid = results['invalid_rows']
    duplicate = results['duplicate_rows']
    
    # Summary
    total = len(valid) + len(invalid) + len(duplicate)
    lines.append(f"**Summary:** {len(valid)} valid, {len(invalid)} invalid, {len(duplicate)} duplicates (total: {total})\n")
    
    # Valid entries
    if valid:
        lines.append(f"### ✅ Valid Entries ({len(valid)})\n")
        lines.append("| Row | Protein | Mutation | Accession | Effect | DOI |")
        lines.append("|-----|---------|----------|-----------|--------|-----|")
        for row in valid:
            doi_short = row['doi'][:20] + '...' if len(row['doi']) > 20 else row['doi']
            lines.append(f"| {row['row_number']} | {row['protein']} | {row['mutation']} | {row['reference_accession']} | {row['effect']} | {doi_short} |")
        lines.append("")
    
    # Invalid entries
    if invalid:
        lines.append(f"### ❌ Invalid Entries ({len(invalid)})\n")
        lines.append("| Row | Protein | Mutation | Effect | DOI | Errors |")
        lines.append("|-----|---------|----------|--------|-----|--------|")
        for row in invalid:
            errors_str = '; '.join(row['errors'])
            doi_short = row['doi'][:15] + '...' if len(row['doi']) > 15 else row['doi']
            lines.append(f"| {row['row_number']} | {row['protein']} | {row['mutation']} | {row['effect']} | {doi_short} | {errors_str} |")
        lines.append("")
    
    # Duplicate entries
    if duplicate:
        lines.append(f"### ⚠️ Duplicate Entries ({len(duplicate)})\n")
        lines.append("These entries already exist in the database and will be skipped:\n")
        lines.append("| Row | Protein | Mutation | DOI |")
        lines.append("|-----|---------|----------|-----|")
        for row in duplicate:
            lines.append(f"| {row['row_number']} | {row['protein']} | {row['mutation']} | {row['doi']} |")
        lines.append("")
    
    # Next steps
    lines.append("---\n")
    if len(valid) > 0 and len(invalid) == 0:
        lines.append("✅ **All entries are valid!** An administrator can add the `accepted` label to merge these mutations into the database.\n")
    elif len(valid) > 0:
        lines.append(f"⚠️ **{len(valid)} valid entries found.** An administrator can add the `accepted` label to merge only the valid mutations.\n")
        lines.append("To include the invalid entries, please fix the errors above and update this issue.\n")
    else:
        lines.append("❌ **No valid entries found.** Please fix the errors above and update this issue.\n")
    
    # Help section
    lines.append("<details><summary>📖 Validation Rules</summary>\n")
    lines.append(f"- **Protein:** Must be one of: {', '.join(VALID_PROTEINS)}")
    lines.append("- **Mutation:** Format `[Letter][Number][Letter]` (e.g., K135E)")
    lines.append(f"- **Effect:** Must be one of: {', '.join(VALID_EFFECTS)}")
    lines.append("- **DOI:** Must be a valid DOI that exists in CrossRef")
    lines.append("</details>")
    
    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_bulk_submission.py <issue_body_file> [existing_tsv] [output_json]")
        sys.exit(1)
    
    issue_body_file = sys.argv[1]
    existing_file = sys.argv[2] if len(sys.argv) > 2 else None
    output_json = sys.argv[3] if len(sys.argv) > 3 else "valid_mutations.json"
    
    # Read issue body
    with open(issue_body_file, 'r', encoding='utf-8') as f:
        body_text = f.read()
    
    # Parse issue body
    parsed = parse_issue_body(body_text)
    tsv_data = parsed.get('TSV Data', '')
    
    if not tsv_data:
        print("## ❌ Error\n\nNo TSV data found in the issue body.")
        sys.exit(1)
    
    # Check for attachment URL
    url_match = re.search(r'(https://[^\s)]+\.(tsv|txt))', tsv_data, re.IGNORECASE)
    if url_match:
        file_url = url_match.group(1)
        print(f"Downloading attachment from: {file_url}", file=sys.stderr)
        try:
            tsv_data = download_attachment(file_url)
        except Exception as e:
            print(f"## ❌ Error\n\nFailed to download attachment: {e}")
            sys.exit(1)
    
    # Validate
    results = validate_bulk_submission(tsv_data, existing_file)
    
    # Generate and print markdown report (for issue comment)
    report = generate_markdown_report(results)
    print(report)
    
    # Save valid rows as JSON (for later merging)
    valid_for_merge = []
    for row in results['valid_rows']:
        valid_for_merge.append({
            'protein': row['protein'],
            'mutation': row['mutation'],
            'reference_accession': row['reference_accession'],
            'effect': row['effect'],
            'doi': row['doi'],
            'notes': row['notes']
        })
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(valid_for_merge, f, indent=2)
    
    print(f"\nSaved {len(valid_for_merge)} valid mutations to {output_json}", file=sys.stderr)
    
    # Exit with appropriate code
    if results['header_error'] or len(results['valid_rows']) == 0:
        sys.exit(1)
    elif len(results['invalid_rows']) > 0:
        sys.exit(2)  # Partial success
    else:
        sys.exit(0)  # Full success


if __name__ == "__main__":
    main()
