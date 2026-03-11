import sys
import json
import re
import requests
import os

def parse_issue_form(body_text):
    """
    Parses a GitHub Issue Form body (Markdown) into a dictionary.
    
    GitHub Issue Forms structure the body with markdown headers corresponding
    to the field labels defined in the YAML template.
    """
    data = {}
    
    # Split by lines and normalize line endings
    lines = body_text.replace('\r\n', '\n').split('\n')
    
    current_key = None
    current_value = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Check for headers (keys)
        if line_stripped.startswith('### '):
            # Save previous key-value pair if it exists
            if current_key:
                val = '\n'.join(current_value).strip()
                if val == "_No response_":
                    val = None
                data[current_key] = val
            
            # Start new key
            current_key = line_stripped[4:].strip()
            current_value = []
        elif current_key:
            # Append line to current value
            current_value.append(line)
            
    # Save the last item
    if current_key:
        val = '\n'.join(current_value).strip()
        if val == "_No response_":
            val = None
        data[current_key] = val
        
    return data

def main():
    # Helper to print usage
    if len(sys.argv) < 2:
        print("Usage: python parse_issue_form.py '<issue_body_text>' OR python parse_issue_form.py --tsv-file <path_to_tsv>")
        sys.exit(1)
        
    normalized_data = {}
    
    # Check for direct TSV file mode
    if sys.argv[1] == "--tsv-file":
        if len(sys.argv) < 3:
             print("Error: Missing file path for --tsv-file")
             sys.exit(1)
        
        file_path = sys.argv[2]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                normalized_data["tsv_data"] = f.read()
        except Exception as e:
            print(f"Error reading TSV file: {e}")
            sys.exit(1)
            
    else:
        # Standard Issue Form Parsing
        issue_body_text = sys.argv[1]
        
        # If the argument is a file path (and not --tsv-file), read it as body text
        try:
            if os.path.exists(issue_body_text):
                with open(issue_body_text, 'r') as f:
                    issue_body_text = f.read()
        except (FileNotFoundError, OSError):
            pass

        parsed_data = parse_issue_form(issue_body_text)
        
        # Map the human-readable labels to the keys expected by the system
        key_mapping = {
            "Protein": "protein",
            "Mutation": "mutation",
            "WT Accession / Sequence ID": "reference_accession",
            "Effect": "effect",
            "Publication DOI": "doi",
            "Additional notes": "notes",
            "TSV Data": "tsv_data"
        }
        
        for label, key in key_mapping.items():
            if label in parsed_data:
                normalized_data[key] = parsed_data[label]
    
    mutations_list = []

    # Check for Bulk Submission
    if "tsv_data" in normalized_data and normalized_data["tsv_data"]:
        tsv_content = normalized_data["tsv_data"].strip()
        
        # Check if the content is a URL (GitHub attachment)
        # Regex to find any https url ending in .tsv or .txt inside the content
        # Matches markdown links [name](url) or plain urls
        # Case insensitive
        url_match = re.search(r'(https://[^\s)]+\.(tsv|txt))', tsv_content, re.IGNORECASE)
        
        if url_match:
            file_url = url_match.group(1)
            print(f"I found an attachment URL: {file_url}")
            try:
                import requests
                
                headers = {}
                token = os.environ.get("GH_TOKEN")
                if token:
                    headers["Authorization"] = f"token {token}"
                    # Also Accept header might be needed for some GitHub APIs, but for raw files often not.
                    # headers["Accept"] = "application/vnd.github.v3.raw" 
                
                print(f"Downloading with headers: {'Authorization: <hidden>' if token else 'None'}")
                response = requests.get(file_url, headers=headers)
                
                if response.status_code != 200:
                    print(f"❌ Failed to download attachment. Status Code: {response.status_code}")
                    print(f"Response: {response.text[:200]}") # Print first 200 chars for debug
                    sys.exit(1)
                    
                tsv_content = response.text
                print("Successfully downloaded attachment content.")
            except Exception as e:
                print(f"❌ Error downloading attachment: {e}")
                sys.exit(1)
        
        lines = [line.strip() for line in tsv_content.strip().split('\n') if line.strip()]
        
        if not lines:
            print("❌ Error: TSV data is empty.")
            sys.exit(1)

        # Validate Header
        header_row = lines[0].lower().split('\t')
        expected_header = ['protein', 'mutation', 'reference_accession', 'effect', 'doi', 'notes']
        
        # Allow some flexibility? No, user said "exactly".
        # But maybe whitespace stripping is okay.
        header_row = [h.strip() for h in header_row]
        
        if header_row != expected_header:
             print(f"❌ Error: Invalid Header Row.")
             print(f"Expected: {expected_header}")
             print(f"Received: {header_row}")
             sys.exit(1)

        # Process rows (skip header)
        for line in lines[1:]:
            parts = line.split('\t')
            # Expected order: protein, mutation, reference_accession, effect, doi, notes
            # Enforce length at least 5 (doi required), notes optional (can be empty string if tab present)
            
            # Pad with empty string if parts are missing (e.g. empty notes at end)
            while len(parts) < 6:
                parts.append("")
                
            entry = {
                "protein": parts[0].strip(),
                "mutation": parts[1].strip(),
                "reference_accession": parts[2].strip(),
                "effect": parts[3].strip(),
                "doi": parts[4].strip(),
                "notes": parts[5].strip()
            }
            mutations_list.append(entry)
    
    # Check for Single Submission (if no bulk data found, or mixed usage?)
    # Prefer Bulk if present, otherwise Single.
    elif "protein" in normalized_data: 
        entry = {
             "protein": normalized_data.get("protein"),
             "mutation": normalized_data.get("mutation"),
             "reference_accession": normalized_data.get("reference_accession"),
             "effect": normalized_data.get("effect"),
             "doi": normalized_data.get("doi"),
             "notes": normalized_data.get("notes")
        }
        mutations_list.append(entry)

    # Print JSON list to stdout
    print(json.dumps(mutations_list, indent=2))

if __name__ == "__main__":
    main()
