import json
import re
import os

def parse_issue_body(body):
    """Extract mutation details from issue body."""
    mutation = re.search(r"Mutation:\s*(.*)", body)
    wt_seq = re.search(r"WT sequence:\s*(.*)", body)
    effect = re.search(r"Effect:\s*(.*)", body)
    publication = re.search(r"Publication:\s*(.*)", body)

    if mutation and wt_seq and effect and publication:
        return [
            mutation.group(1).strip().replace("\r", ""),
            wt_seq.group(1).strip().replace("\r", ""),
            effect.group(1).strip().replace("\r", ""),
            publication.group(1).strip().replace("\r", "")
        ]
    return None

def main():
    with open("issues.json") as f:
        issues = json.load(f)

    parsed_issues = [["Mutation", "WT Sequence", "Effect", "Publication"]]  # Add headers
    for issue in issues:
        body = issue.get("body", "")
        parsed_entry = parse_issue_body(body)
        if parsed_entry:
            parsed_issues.append(parsed_entry)

    # Ensure docs directory exists
    os.makedirs("docs", exist_ok=True)

    # Save the TSV file to the docs directory
    with open("docs/parsed_issues.tsv", "w", newline='') as f:
        for row in parsed_issues:
            f.write("\t".join(row) + "\n")

if __name__ == "__main__":
    main()
