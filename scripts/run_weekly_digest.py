import os
import sys
import datetime
import requests
from datetime import timedelta

# Add project root to sys.path to allow imports from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.digest_core import (
    load_env_file,
    fetch_github_commits,
    fetch_org_commits,
    fetch_trello_notes,
    fetch_trello_actions,
    trello_post,
    trello_get
)

def get_last_week_dates():
    """Return (start_iso, end_iso) for the previous week (Monday to Sunday)."""
    today = datetime.date.today()
    # Monday = 0, Sunday = 6
    # If today is Monday (0), last week Monday was today - 7
    # If today is Tuesday (1), last week Monday was today - 8
    # Start of last week: today - timedelta(days=today.weekday() + 7)
    start_date = today - timedelta(days=today.weekday() + 7)
    end_date = start_date + timedelta(days=6)
    
    # Format as ISO 8601 strings (YYYY-MM-DD)
    return start_date.isoformat(), end_date.isoformat()

def format_meeting_notes(notes):
    if not notes:
        return "No meeting notes."
    lines = []
    for c in notes:
        date = c.get('titleDate') or c.get('dateLastActivity') or ''
        link = f"[link]({c.get('url')})" if c.get('url') else ''
        desc = c.get('desc') or ''
        lines.append(f"- {date} {c.get('name')} {link}\n  {desc}")
    return "\n\n".join(lines)

def format_commits(groups):
    if not groups:
        return "No commits."
    lines = []
    for g in groups:
        header = f"### {g.get('repo')} ({g.get('branch')})"
        commits = []
        for c in g.get('commits', []):
            msg = (c.get('message') or '').split('\n')[0].strip()
            link = f"[link]({c.get('url')})" if c.get('url') else ''
            commits.append(f"- {c.get('date')} {c.get('author')}: {msg} {link}")
        lines.append(f"{header}\n" + "\n".join(commits))
    return "\n\n".join(lines)

def format_actions(groups):
    if not groups:
        return "No actions."
    lines = []
    for g in groups:
        header = f"### {g.get('column')}"
        cards = []
        for c in g.get('cards', []):
            card_header = f"#### {c.get('name')}"
            actions = []
            for a in c.get('actions', []):
                text = f"{a.get('date')} · {a.get('member')} · {a.get('type')}"
                if a.get('text'):
                    text += f" · {a.get('text')}"
                actions.append(f"- {text}")
            cards.append(f"{card_header}\n" + "\n".join(actions))
        lines.append(f"{header}\n" + "\n\n".join(cards))
    return "\n\n".join(lines)

def generate_markdown_report(start_date, end_date, notes, org_groups, action_groups):
    report = f"# Weekly Digest ({start_date} to {end_date})\n\n"
    
    report += "## Transcripts Summary\n\n"
    report += format_meeting_notes(notes) + "\n\n"
    
    report += "## GitHub Commits\n\n"
    report += format_commits(org_groups) + "\n\n"
    
    report += "## Trello Activity\n\n"
    report += format_actions(action_groups) + "\n"
    
    return report

def main():
    load_env_file()
    
    # Configuration
    GITHUB_ORG = os.getenv('GITHUB_ORG', 'zcashme')
    TRELLO_BOARD = os.getenv('TRELLO_BOARD', 'Zcash Me')
    TRELLO_NOTES_LIST = os.getenv('TRELLO_NOTES_LIST', 'Meeting Notes')
    TRELLO_TARGET_LIST_ID = os.getenv('TRELLO_TARGET_LIST_ID')
    
    start_date, end_date = get_last_week_dates()
    print(f"Generating digest for: {start_date} to {end_date}")
    
    # 1. Fetch Data
    print("Fetching GitHub commits...")
    try:
        repo_commits = fetch_github_commits('ZcashUsersGroup', 'zcashme', 'main', start_date, end_date)
        repo_group = {
            'repo': 'zcashme', 
            'url': 'https://github.com/ZcashUsersGroup/zcashme', 
            'branch': 'main', 
            'commits': repo_commits
        }
        
        org_groups_raw = fetch_org_commits(GITHUB_ORG, start_date, end_date)
        org_groups = [repo_group] + org_groups_raw
    except Exception as e:
        print(f"Error fetching GitHub data: {e}")
        org_groups = []

    print("Fetching Trello meeting notes...")
    try:
        notes = fetch_trello_notes(TRELLO_BOARD, TRELLO_NOTES_LIST, start_date, end_date)
    except Exception as e:
        print(f"Error fetching Trello notes: {e}")
        notes = []

    print("Fetching Trello board actions...")
    try:
        action_groups = fetch_trello_actions(TRELLO_BOARD, start_date, end_date, in_progress_list='In Progress', completed_list='Completed')
    except Exception as e:
        print(f"Error fetching Trello actions: {e}")
        action_groups = []

    # 2. Generate Report
    report_md = generate_markdown_report(start_date, end_date, notes, org_groups, action_groups)
    
    # 3. Publish to Trello or Save Locally
    print("Publishing...")

    target_list_id = TRELLO_TARGET_LIST_ID

    if not target_list_id:
        print("TRELLO_TARGET_LIST_ID not set. Searching for 'Inbox' list...")
        try:
            # Find board first
            boards = trello_get('https://api.trello.com/1/members/me/boards')
            board = next((b for b in boards if (b.get('name') or '').lower() == TRELLO_BOARD.lower()), None)
            if board:
                lists = trello_get(f'https://api.trello.com/1/boards/{board.get("id")}/lists')
                inbox_list = next((l for l in lists if (l.get('name') or '').lower() == 'inbox'), None)
                if inbox_list:
                    target_list_id = inbox_list.get('id')
                    print(f"Found 'Inbox' list: {target_list_id}")
                else:
                    print(f"List 'Inbox' not found on board '{TRELLO_BOARD}'.")
            else:
                print(f"Board '{TRELLO_BOARD}' not found.")
        except Exception as e:
            print(f"Error searching for Inbox list: {e}")
    
    if target_list_id:
        card_title = f"Weekly Digest: {start_date} - {end_date}"
        try:
            # Create Card
            card_data = {
                'idList': target_list_id,
                'name': card_title,
                'desc': report_md[:16000] # Trello limit is 16384 chars
            }
            new_card = trello_post('https://api.trello.com/1/cards', data=card_data)
            print(f"Card created: {new_card.get('url')}")
            
            # Attach full report as file
            files = {
                'file': (f'weekly-digest-{start_date}.md', report_md, 'text/markdown')
            }
            params = {
                'key': os.getenv('TRELLO_KEY'),
                'token': os.getenv('TRELLO_TOKEN')
            }
            requests.post(f"https://api.trello.com/1/cards/{new_card['id']}/attachments", params=params, files=files)
            print("Report attached to card.")
            
        except Exception as e:
            print(f"Error publishing to Trello: {e}")
    else:
        print("Target list not found. Saving locally.")
        
        # Ensure reports directory exists
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
            
        filename = f"weekly-digest-{start_date}.md"
        filepath = os.path.join(reports_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"Saved to {filepath}")

if __name__ == "__main__":
    main()
