"""
Generate contributor statistics from GitHub issues.
Fetches all closed issues with 'accepted' label and creates a contributors JSON file.
"""

import os
import json
import requests
from collections import defaultdict
from datetime import datetime

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
REPO = os.environ.get('GITHUB_REPOSITORY', '')

# Try to infer repo from git remote if not set
if not REPO:
    try:
        import subprocess
        result = subprocess.run(['git', 'config', '--get', 'remote.origin.url'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            url = result.stdout.strip()
            # Parse GitHub URL (handles both HTTPS and SSH)
            if 'github.com' in url:
                parts = url.replace('.git', '').replace(':', '/').split('/')
                if len(parts) >= 2:
                    REPO = f"{parts[-2]}/{parts[-1]}"
    except Exception:
        pass

if not REPO:
    print("Warning: Could not determine repository. Please set GITHUB_REPOSITORY environment variable.")
    REPO = "Centre-for-Virus-Research/FMED"  # Default fallback

API_URL = f"https://api.github.com/repos/{REPO}/issues"
OUTPUT_FILE = "docs/api/contributors.json"

def load_existing_data():
    """Load existing contributors.json if it exists."""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load existing file: {e}")
    return None

def fetch_accepted_issues():
    """Fetch all closed issues with 'accepted' label."""
    headers = {
        'Accept': 'application/vnd.github.v3+json'
    }
    if GITHUB_TOKEN:
        headers['Authorization'] = f'Bearer {GITHUB_TOKEN}'
    
    params = {
        'state': 'closed',
        'labels': 'accepted',
        'per_page': 100,
        'page': 1
    }
    
    all_issues = []
    
    while True:
        response = requests.get(API_URL, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Error fetching issues: {response.status_code}")
            break
        
        issues = response.json()
        if not issues:
            break
        
        all_issues.extend(issues)
        
        # Check for next page
        if 'Link' in response.headers:
            links = response.headers['Link']
            if 'rel="next"' not in links:
                break
            params['page'] += 1
        else:
            break
    
    return all_issues

def parse_mutations_from_issue(issue):
    """Extract number of mutations from an issue."""
    # Check if it's a bulk submission
    labels = [label['name'] for label in issue.get('labels', [])]
    
    if 'bulk' in labels:
        # Parse TSV or count from body
        body = issue.get('body', '')
        # Count lines that look like mutations (simple heuristic)
        lines = body.strip().split('\n')
        mutation_lines = [l for l in lines if '\t' in l and not l.startswith('protein')]
        return max(len(mutation_lines), 1)
    else:
        # Single mutation submission
        return 1

def generate_contributor_stats(issues,existing_contributors=None, processed_issue_ids=None):
    """Generate contributor statistics from issues (incremental update support)."""
    if processed_issue_ids is None:
        processed_issue_ids = set()
    
    # Initialize  contributors from existing data or start fresh
    contributors = defaultdict(lambda: {
        'username': '',
        'name': '',
        'avatar_url': '',
        'profile_url': '',
        'mutations_contributed': 0,
        'issues_submitted': 0,
        'first_contribution': None,
        'last_contribution': None,
        'issue_ids': []
    })
    
    # Load existing contributors
    if existing_contributors:
        for c in existing_contributors:
            contributors[c['username']] = c.copy()
            if 'issue_ids' not in contributors[c['username']]:
                contributors[c['username']]['issue_ids'] = []
    
    for issue in issues:
        issue_id = issue['number']
        
        # Skip if already processed
        if issue_id in processed_issue_ids:
            continue
        
        user = issue.get('user', {})
        username = user.get('login', 'unknown')
        
        contributor = contributors[username]
        contributor['username'] = username
        contributor['name'] = user.get('name') or username
        contributor['avatar_url'] = user.get('avatar_url', '')
        contributor['profile_url'] = user.get('html_url', '')
        
        # Count mutations for this new issue
        mutations_count = parse_mutations_from_issue(issue)
        contributor['mutations_contributed'] += mutations_count
        contributor['issues_submitted'] += 1
        contributor['issue_ids'].append(issue_id)
        
        # Track dates
        closed_at = issue.get('closed_at')
        if closed_at:
            if not contributor['first_contribution'] or closed_at < contributor['first_contribution']:
                contributor['first_contribution'] = closed_at
            if not contributor['last_contribution'] or closed_at > contributor['last_contribution']:
                contributor['last_contribution'] = closed_at
    
    # Convert to list and sort by most recent contribution
    contributor_list = list(contributors.values())
    contributor_list.sort(key=lambda x: x['last_contribution'] or '', reverse=True)
    
    return contributor_list

def main():
    # Load existing data for incremental updates
    existing_data = load_existing_data()
    
    if existing_data:
        print(f"📂 Loaded existing data (last updated: {existing_data.get('generated_at', 'unknown')})")  
        existing_contributors = existing_data.get('contributors', [])
        
        # Get all processed issue IDs  
        processed_issue_ids = set()
        for c in existing_contributors:
            if 'issue_ids' in c:
                processed_issue_ids.update(c['issue_ids'])
        
        print(f"🔄 Fetching all accepted issues to check for updates...")
        issues = fetch_accepted_issues()
        unprocessed = [i for i in issues if i['number'] not in processed_issue_ids]
        print(f"Found {len(issues)} total accepted issues, {len(unprocessed)} new")
        
        print("📊 Updating contributor statistics...")
        contributors = generate_contributor_stats(issues, existing_contributors, processed_issue_ids)
    else:
        print("🆕 No existing data found, generating from scratch...")
        print("Fetching accepted issues from GitHub...")
        issues = fetch_accepted_issues()
        print(f"Found {len(issues)} accepted issues")
        
        print("Generating contributor statistics...")
        contributors = generate_contributor_stats(issues)
    
    print(f"Found {len(contributors)} contributors")
    
    # Create output structure
    output = {
        'generated_at': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        'total_contributors': len(contributors),
        'total_mutations': sum(c['mutations_contributed'] for c in contributors),
        'total_issues': sum(c['issues_submitted'] for c in contributors),
        'contributors': contributors
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Generated contributor statistics in {OUTPUT_FILE}")
    print(f"   - {output['total_contributors']} contributors")
    print(f"   - {output['total_mutations']} total mutations")
    print(f"   - {output['total_issues']} total issues")

if __name__ == "__main__":
    main()
