import requests
import sys

def get_doi_details(doi):
    api_url = f"https://api.crossref.org/works/{doi}"
    response = requests.get(api_url)

    if response.status_code == 200:
        data = response.json().get('message', {})
        title = data.get('title', ['No title found'])[0]
        authors = ', '.join(
            f"{author['given']} {author['family']}" 
            for author in data.get('author', [])
        )
        journal = data.get('container-title', ['No journal found'])[0]
        print(f"Title: {title}")
        print(f"Authors: {authors}")
        print(f"Journal: {journal}")
    else:
        print(f"Error: DOI {doi} not found or invalid")

# Example usage
if __name__ == "__main__":
    if len(sys.argv) > 1:
        doi = sys.argv[1]
        get_doi_details(doi)
    else:
        print("Usage: python get_doi_details.py <DOI>")
        print("Example: python get_doi_details.py 10.1080/22221751.2025.2455596")
