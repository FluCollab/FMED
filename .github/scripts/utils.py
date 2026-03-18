"""
Shared utilities for FMED scripts.

This module provides common functions used across multiple scripts to ensure
consistent behavior and reduce code duplication.
"""

import csv
import os
import requests
import time

# =============================================================================
# Constants
# =============================================================================

# Valid influenza proteins (matching issue template)
VALID_PROTEINS = ['HA', 'NA', 'PB2', 'PB1', 'PA', 'NP', 'M1', 'M2', 'NS1', 'NS2']

# Required columns for the mutation database
REQUIRED_COLUMNS = ["protein", "mutation", "reference_accession", "effect", "source_publication", "notes"]

# CrossRef API configuration
CROSSREF_API_BASE = "https://api.crossref.org/works"
CROSSREF_TIMEOUT = 10  # seconds
CROSSREF_RETRY_DELAY = 1  # seconds between retries
CROSSREF_MAX_RETRIES = 3

# Valid effect categories (matching issue template dropdown)
VALID_EFFECTS = [
    'Mammalian adaptation',
    'Increased binding',
    'Avian adaptation',
    'Drug resistance',
    'Antigenic escape mutation',
    'Other'
]


# =============================================================================
# Text Normalization Functions
# =============================================================================

def normalize_line_endings(text):
    """
    Normalizes line endings in text to Unix-style (LF).
    
    Handles Windows (CRLF), Mac OS Classic (CR), and Unix (LF) line endings.
    This ensures consistent parsing regardless of the source platform.
    
    Args:
        text: String with potentially mixed line endings
        
    Returns:
        String with normalized LF line endings
    """
    if not text:
        return text
    # Replace Windows CRLF with LF, then any remaining CR with LF
    return text.replace('\r\n', '\n').replace('\r', '\n')


# =============================================================================
# Validation Functions
# =============================================================================

def validate_protein(protein):
    """
    Validates that a protein is a valid influenza protein.
    
    Args:
        protein: The protein name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not protein:
        return False
    return protein.upper() in VALID_PROTEINS


def validate_mutation(mutation):
    """
    Validates mutation format: single letter, digits, single letter (e.g., K135E).
    
    Args:
        mutation: The mutation string to validate
        
    Returns:
        True if format is valid, False otherwise
    """
    import re
    if not mutation:
        return False
    # Pattern: one uppercase letter, one or more digits, one uppercase letter
    pattern = r'^[A-Z]\d+[A-Z]$'
    return bool(re.match(pattern, mutation.strip().upper()))


def validate_effect(effect):
    """
    Validates that an effect is in the allowed categories.
    
    Args:
        effect: The effect string to validate
        
    Returns:
        True if effect matches an allowed category, False otherwise
    """
    if not effect:
        return False
    # Case-insensitive comparison
    effect_lower = effect.strip().lower()
    return any(e.lower() == effect_lower for e in VALID_EFFECTS)


def validate_row(row, validate_doi_online=True):
    """
    Validates all fields in a mutation row.
    
    Args:
        row: Dictionary with mutation data (protein, mutation, effect, doi/source_publication)
        validate_doi_online: If True, validate DOI against CrossRef (slower)
        
    Returns:
        Tuple of (is_valid, errors_list)
        - is_valid: True if all validations pass
        - errors_list: List of error strings describing what failed
    """
    errors = []
    
    # Validate protein
    protein = row.get('protein', '').strip()
    if not validate_protein(protein):
        errors.append(f"Invalid protein '{protein}'")
    
    # Validate mutation format
    mutation = row.get('mutation', '').strip()
    if not validate_mutation(mutation):
        errors.append(f"Invalid mutation format '{mutation}' (expected format: K135E)")
    
    # Validate effect
    effect = row.get('effect', '').strip()
    if not validate_effect(effect):
        errors.append(f"Invalid effect '{effect}'")
    
    # Validate DOI
    doi = row.get('doi', '') or row.get('source_publication', '')
    doi = doi.strip() if doi else ''
    if not doi:
        errors.append("Missing DOI")
    elif validate_doi_online:
        if not validate_doi(doi, verbose=False):
            errors.append(f"DOI not found in CrossRef")
    
    return (len(errors) == 0, errors)


def validate_doi(doi, verbose=True):
    """
    Validates a DOI using the CrossRef API with retry logic.
    
    Args:
        doi: The DOI to validate (e.g., "10.1128/jvi.01234-21")
        verbose: If True, print status messages
        
    Returns:
        True if the DOI exists in CrossRef, False otherwise
    """
    if not doi or not doi.strip():
        if verbose:
            print("❌ DOI is empty or missing")
        return False
    
    doi = doi.strip()
    url = f"{CROSSREF_API_BASE}/{doi}"
    
    if verbose:
        print(f"🔍 Validating DOI: {doi}...")
    
    for attempt in range(CROSSREF_MAX_RETRIES):
        try:
            response = requests.get(url, timeout=CROSSREF_TIMEOUT)
            
            if response.status_code == 200:
                if verbose:
                    print("✅ DOI is valid.")
                return True
            elif response.status_code == 404:
                if verbose:
                    print(f"❌ DOI not found in CrossRef: {doi}")
                return False
            elif response.status_code == 429:
                # Rate limited - wait and retry
                if verbose:
                    print(f"⚠️ Rate limited, waiting before retry...")
                time.sleep(CROSSREF_RETRY_DELAY * (attempt + 1))
                continue
            else:
                if verbose:
                    print(f"⚠️ CrossRef API returned status {response.status_code}")
                # Fail closed on unexpected status codes
                return False
                
        except requests.Timeout:
            if verbose:
                print(f"⚠️ Timeout checking DOI (attempt {attempt + 1}/{CROSSREF_MAX_RETRIES})")
            if attempt < CROSSREF_MAX_RETRIES - 1:
                time.sleep(CROSSREF_RETRY_DELAY)
                continue
            return False
        except requests.RequestException as e:
            if verbose:
                print(f"⚠️ Network error checking DOI: {e}")
            return False
    
    return False


def get_doi_metadata(doi, verbose=True):
    """
    Fetches metadata for a DOI from CrossRef API.
    
    Args:
        doi: The DOI to look up
        verbose: If True, print status messages
        
    Returns:
        Dictionary with metadata or None if not found:
        {
            'title': str,
            'authors': str (comma-separated),
            'journal': str,
            'year': int or str,
            'doi_url': str
        }
    """
    if not doi or not doi.strip():
        return None
    
    doi = doi.strip()
    url = f"{CROSSREF_API_BASE}/{doi}"
    
    try:
        response = requests.get(url, timeout=CROSSREF_TIMEOUT)
        
        if response.status_code != 200:
            if verbose:
                print(f"Error: DOI {doi} not found or invalid")
            return None
            
        data = response.json().get('message', {})
        
        # Extract title
        title = data.get('title', ['No title found'])
        title = title[0] if title else 'No title found'
        
        # Extract authors
        authors_list = data.get('author', [])
        authors = ', '.join(
            f"{author.get('given', '')} {author.get('family', '')}".strip()
            for author in authors_list
            if author.get('family')  # Only include if has family name
        )
        if not authors:
            authors = 'No authors found'
        
        # Extract journal
        journal = data.get('container-title', ['No journal found'])
        journal = journal[0] if journal else 'No journal found'
        
        # Extract year (try print first, then online)
        year = None
        for date_field in ['published-print', 'published-online', 'created']:
            date_parts = data.get(date_field, {}).get('date-parts', [[None]])
            if date_parts and date_parts[0] and date_parts[0][0]:
                year = date_parts[0][0]
                break
        if year is None:
            year = 'No year found'
        
        return {
            'title': title,
            'authors': authors,
            'journal': journal,
            'year': year,
            'doi_url': f"https://doi.org/{doi}"
        }
        
    except requests.RequestException as e:
        if verbose:
            print(f"Error fetching DOI metadata: {e}")
        return None


# =============================================================================
# TSV File Functions
# =============================================================================

def read_tsv(file_path, normalize_columns=True):
    """
    Reads a TSV file into a list of dictionaries.
    
    Args:
        file_path: Path to the TSV file
        normalize_columns: If True, normalize column names to REQUIRED_COLUMNS
        
    Returns:
        List of dictionaries, one per row
    """
    data = []
    
    if not os.path.exists(file_path):
        return data
    
    with open(file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter="\t")
        
        for row in reader:
            if normalize_columns:
                entry = {}
                for col in REQUIRED_COLUMNS:
                    val = row.get(col)
                    
                    # Handle doi -> source_publication mapping
                    if val is None and col == "source_publication":
                        val = row.get("doi", "")
                    elif val is None:
                        val = ""
                    
                    entry[col] = val
                data.append(entry)
            else:
                data.append(dict(row))
    
    return data


def write_tsv(file_path, data, columns=None):
    """
    Writes a list of dictionaries to a TSV file.
    
    Args:
        file_path: Path to write the TSV file
        data: List of dictionaries to write
        columns: Column order (defaults to REQUIRED_COLUMNS)
    """
    if columns is None:
        columns = REQUIRED_COLUMNS
    
    with open(file_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, delimiter="\t", extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)


# =============================================================================
# Duplicate Detection
# =============================================================================

def is_duplicate(entry, existing_data):
    """
    Check if an entry already exists in the dataset.
    
    Duplicates are detected by matching protein, mutation, effect, and source_publication.
    
    Args:
        entry: Dictionary with mutation data
        existing_data: List of existing entries
        
    Returns:
        True if duplicate exists, False otherwise
    """
    for row in existing_data:
        if (row.get("protein") == entry.get("protein") and
            row.get("mutation") == entry.get("mutation") and
            row.get("effect") == entry.get("effect") and
            row.get("source_publication") == entry.get("source_publication")):
            return True
    return False

