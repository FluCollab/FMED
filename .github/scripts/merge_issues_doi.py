import sys
import csv
import os
import base64
import requests
import re

# Update REQUIRED_COLUMNS to include the new columns
REQUIRED_COLUMNS = ["protein", "mutation", "reference_accession", "effect", "source_publication"]
OUTPUT_COLUMNS = ["protein", "mutation", "reference_accession", "effect", "source_publication", "author", "year", "title", "journal", "doi_url"]

DOI_PATTERN = r"^10.\d{4,9}/[-._;()/:\w]+$"  # Regex pattern for valid DOI

def read_tsv(file_path):
    """Reads a TSV file into a list of dictionaries and ensures column order."""
    data = []

    if not os.path.exists(file_path):
        return data  # Return empty list if file doesn't exist

    with open(file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter="\t")
        for row in reader:
            # Ensure the row follows the required column order
            ordered_row = {col: row.get(col, "Unknown" if col == "protein" else "") for col in REQUIRED_COLUMNS}
            data.append(ordered_row)

    return data

def write_tsv(file_path, data):
    """Writes a list of dictionaries to a TSV file with a fixed column order."""
    with open(file_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REQUIRED_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(data)

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
    issue_body = decode_base64(issue_body)
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
        return None  # Indicate invalid data

def validate_dois(data):
    """Validates DOI format after merging and updates the dataset accordingly."""
    for entry in data:
        doi = entry.get("source_publication", "").strip()
        if doi and re.match(DOI_PATTERN, doi):
            api_url = f"https://api.crossref.org/works/{doi}"
            response = requests.get(api_url)

            if response.status_code == 200:
                doi_data = response.json().get('message', {})
                title = doi_data.get('title', ['No title found'])[0]
                authors = ', '.join(
                    f"{author['given']} {author['family']}" 
                    for author in doi_data.get('author', [])
                )
                journal = doi_data.get('container-title', ['No journal found'])[0]
                year = doi_data.get('published-print', {}).get('date-parts', [[None]])[0][0] or "No year found"
                entry["title"] = title
                entry["author"] = authors
                entry["journal"] = journal
                entry["year"] = year
                entry["doi_url"] = f"https://doi.org/{doi}"
                entry["source_publication"] = f"{authors} ({year}). {journal}. [DOI Link](https://doi.org/{doi})"
            else:
                print(f"⚠️ DOI {doi} not found or invalid. Marking as INVALID_DOI.")
                entry["source_publication"] = "INVALID_DOI"
                entry["title"] = "INVALID_DOI"
                entry["author"] = "INVALID_DOI"
                entry["journal"] = "INVALID_DOI"
                entry["year"] = "INVALID_DOI"
                entry["doi_url"] = "INVALID_DOI"
        elif doi:
            print(f"⚠️ Invalid DOI format found: {doi}")
            entry["source_publication"] = "INVALID_DOI"
            entry["title"] = "INVALID_DOI"
            entry["author"] = "INVALID_DOI"
            entry["journal"] = "INVALID_DOI"
            entry["year"] = "INVALID_DOI"
            entry["doi_url"] = "INVALID_DOI"
    return data


def merge_issues(existing_file, issue_body, new_data_file=None):
    """Merges issue data into an existing TSV dataset while preserving column order."""
    print(f"Received Arguments:")
    print(f"  - Existing File: {existing_file}")
    print(f"  - Issue Body: {issue_body if issue_body else '(No issue body provided)'}")
    print(f"  - New Data File: {new_data_file if new_data_file else '(No attachment provided)'}")

    existing_data = read_tsv(existing_file)

    # Load new data
    if new_data_file:
        new_data = read_tsv(new_data_file)
        print(new_data)
    else:
        parsed_issue = parse_issue_body(issue_body)
        if parsed_issue:
            new_data = [parsed_issue]
        else:
            return

    # Deduplicate by 'mutation' while keeping column order
    unique_data = {entry["mutation"]: entry for entry in existing_data + new_data}.values()

    # Validate DOIs after merging and deduplication
    validated_data = validate_dois(list(unique_data))

    # Save the updated dataset
    write_tsv(existing_file, list(validated_data))
    print("✅ Merged, deduplicated, and validated DOIs in parsed_issues.tsv!")

if __name__ == "__main__":
    merge_issues(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
