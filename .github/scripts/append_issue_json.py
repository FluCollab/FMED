"""
Appends a mutation entry from JSON to the parsed_issues TSV file.
"""

import sys
import json
import os

from utils import (
    REQUIRED_COLUMNS,
    validate_doi,
    read_tsv,
    write_tsv,
    is_duplicate
)


def main():
    if len(sys.argv) < 3:
        print("Usage: python append_issue_json.py <tsv_file> <json_file_or_string>")
        sys.exit(1)

    tsv_file = sys.argv[1]
    json_input = sys.argv[2]

    # Load JSON data
    try:
        if os.path.exists(json_input):
            with open(json_input, 'r') as f:
                new_entry = json.load(f)
        else:
            new_entry = json.loads(json_input)
    except json.JSONDecodeError as e:
        print(f"❌ Error decoding JSON: {e}")
        sys.exit(1)

    # Normalize keys to match TSV columns
    normalized_entry = {
        "protein": new_entry.get("protein"),
        "mutation": new_entry.get("mutation"),
        "reference_accession": new_entry.get("reference_accession"),
        "effect": new_entry.get("effect"),
        "source_publication": new_entry.get("doi"),
        "notes": new_entry.get("notes", "")
    }

    # Validate required fields (exclude notes)
    required_fields = ["protein", "mutation", "reference_accession", "effect", "source_publication"]
    missing_fields = [field for field in required_fields if not normalized_entry.get(field)]
    
    if missing_fields:
        print(f"❌ Missing required fields in JSON input: {missing_fields}")
        print(f"Input: {normalized_entry}")
        sys.exit(1)

    # Validate DOI
    if not validate_doi(normalized_entry["source_publication"]):
        print("❌ Validation Failed: Invalid or unreachable DOI. Entry was NOT added.")
        sys.exit(1)

    print(f"Processing: {normalized_entry['protein']} {normalized_entry['mutation']}")

    # Read existing data
    data = read_tsv(tsv_file)

    # Check for duplicates
    if is_duplicate(normalized_entry, data):
        print("⚠️ Entry already exists. Skipping.")
    else:
        data.append(normalized_entry)
        write_tsv(tsv_file, data)
        print("✅ Successfully appended new mutation to database.")


if __name__ == "__main__":
    main()
