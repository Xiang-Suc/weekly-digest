import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, make_response
import requests

# --- simple .env loader (no external deps) ---
def load_env_file(path='.env'):
    try:
        if not os.path.exists(path):
            return
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith('#'):
                    continue
                if '=' not in s:
                    continue
                k, v = s.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and (k not in os.environ or not os.environ.get(k)):
                    os.environ[k] = v
    except Exception:
        # ignore .env parse errors to avoid blocking server
        pass

# Load env from local .env if present
load_env_file()

app = Flask(__name__)

# Simple CORS for local dev and GitHub Pages
@app.after_request
def add_cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return resp

@app.route('/api/github/commits', methods=['GET', 'OPTIONS'])
def github_commits():
    if request.method == 'OPTIONS':
        return make_response('', 204)

    owner = request.args.get('owner', '').strip()
    repo = request.args.get('repo', '').strip()
    branch = request.args.get('branch', 'main').strip()
    since = request.args.get('since', '').strip()
    until = request.args.get('until', '').strip()

    if not owner or not repo or not since or not until:
        return jsonify({ 'error': 'Missing required params: owner, repo, since, until' }), 400

    token = os.getenv('GITHUB_TOKEN', '').strip()
    headers = {
        'Accept': 'application/vnd.github+json',
        **({ 'Authorization': f'Bearer {token}' } if token else {})
    }

    commits = []
    page = 1
    try:
        while page < 10:
            url = f"https://api.github.com/repos/{owner}/{repo}/commits?sha={branch}&since={since}&until={until}&per_page=100&page={page}"
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code >= 400:
                return jsonify({ 'error': f'GitHub HTTP {r.status_code}', 'details': r.text }), r.status_code
            batch = r.json()
            commits.extend(batch)
            if len(batch) < 100:
                break
            page += 1
    except requests.RequestException as e:
        return jsonify({ 'error': 'GitHub request failed', 'details': str(e) }), 502

    def to_utc_iso(s):
        try:
            return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone().isoformat().replace('+00:00', 'Z')
        except Exception:
            try:
                return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S%z').astimezone().isoformat().replace('+00:00', 'Z')
            except Exception:
                return s or ''

    normalized = []
    for c in commits:
        msg = (c.get('commit') or {}).get('message', '')
        author_name = ((c.get('commit') or {}).get('author') or {}).get('name') or (c.get('author') or {}).get('login') or ''
        author_date = ((c.get('commit') or {}).get('author') or {}).get('date') or ''
        normalized.append({
            'sha': c.get('sha'),
            'url': c.get('html_url'),
            'message': msg,
            'author': author_name,
            'date': to_utc_iso(author_date)
        })

    return jsonify(normalized)

# --- Trello proxy ---

def trello_get(url, params=None):
    key = os.getenv('TRELLO_KEY', '').strip()
    token = os.getenv('TRELLO_TOKEN', '').strip()
    if not key or not token:
        raise ValueError('Missing TRELLO_KEY/TRELLO_TOKEN')
    params = params or {}
    params.update({'key': key, 'token': token})
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

@app.route('/api/trello/meeting-notes', methods=['GET', 'POST', 'OPTIONS'])
def trello_meeting_notes():
    if request.method == 'OPTIONS':
        return make_response('', 204)
    if request.method == 'POST':
        data = request.get_json(force=True) or {}
        board_name = (data.get('boardName') or '').strip()
        list_name = (data.get('listName') or '').strip()
        since = (data.get('since') or '').strip()
        until = (data.get('until') or '').strip()
    else:
        board_name = (request.args.get('boardName') or '').strip()
        list_name = (request.args.get('listName') or '').strip()
        since = (request.args.get('since') or '').strip()
        until = (request.args.get('until') or '').strip()
    if not board_name or not list_name or not since or not until:
        return jsonify({'error': 'Missing required params: boardName, listName, since, until'}), 400

    try:
        boards = trello_get('https://api.trello.com/1/members/me/boards')
        board = next((b for b in boards if (b.get('name') or '').lower() == board_name.lower()), None)
        if not board:
            return jsonify({'error': f'Board not found: {board_name}'}), 404
        lists = trello_get(f'https://api.trello.com/1/boards/{board.get("id")}/lists')
        lst = next((l for l in lists if (l.get('name') or '').lower() == list_name.lower()), None)
        if not lst:
            return jsonify({'error': f'List not found: {list_name}'}), 404
        cards = trello_get(f'https://api.trello.com/1/lists/{lst.get("id")}/cards', params={'fields': 'name,desc,dateLastActivity,shortUrl'})

        since_t = datetime.fromisoformat(since.replace('Z', '+00:00')).timestamp()
        until_t = datetime.fromisoformat(until.replace('Z', '+00:00')).timestamp()

        def to_utc_iso(s):
            try:
                return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone().isoformat().replace('+00:00', 'Z')
            except Exception:
                try:
                    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S%z').astimezone().isoformat().replace('+00:00', 'Z')
                except Exception:
                    return s or ''

        results = []
        for c in cards:
            act_str = c.get('dateLastActivity') or c.get('date') or ''
            try:
                act_ts = datetime.fromisoformat(act_str.replace('Z', '+00:00')).timestamp()
            except Exception:
                act_ts = 0
            if not act_ts or act_ts < since_t or act_ts >= until_t:
                continue
            comments = trello_get(f'https://api.trello.com/1/cards/{c.get("id")}/actions', params={'filter': 'commentCard', 'limit': 1000, 'since': since, 'before': until})
            attachments = trello_get(f'https://api.trello.com/1/cards/{c.get("id")}/attachments')
            results.append({
                'cardId': c.get('id'),
                'name': c.get('name'),
                'url': c.get('shortUrl'),
                'dateLastActivity': to_utc_iso(c.get('dateLastActivity') or ''),
                'desc': c.get('desc') or '',
                'comments': [
                    {
                        'text': (a.get('data') or {}).get('text') or '',
                        'date': to_utc_iso(a.get('date') or ''),
                        'member': ((a.get('memberCreator') or {}).get('fullName') or '')
                    }
                    for a in comments
                ],
                'attachments': [
                    {
                        'name': att.get('name'),
                        'url': att.get('url') or att.get('downloadUrl') or '',
                        'mimeType': att.get('mimeType') or ''
                    }
                    for att in attachments
                ],
            })
        return jsonify(results)
    except requests.HTTPError as e:
        return jsonify({'error': 'Trello HTTP error', 'details': str(e)}), 502
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Unexpected trello error', 'details': str(e)}), 500

# --- OpenAI proxy ---

def build_user_content(input_obj):
    week = (input_obj or {}).get('week') or {}
    transcripts = (input_obj or {}).get('transcripts') or []
    github = (input_obj or {}).get('github') or []
    trello = (input_obj or {}).get('trello') or []
    header = (
        f"Generate a weekly digest (WDWDLW) covering {week.get('startDate')} → {week.get('endDate')}\n"
        "Integrate: transcripts, GitHub commits (main), Trello Meeting Notes.\n"
        "Use precise, audit-friendly Markdown. Keep sections: Week Range, Overview, Daily Log, Cross-Week, References."
    )
    def slice_text(s, n):
        s = str(s or '')
        return (s[:n] + '…') if len(s) > n else s
    def first_line(s):
        return str(s or '').split('\n')[0].strip()
    tx = '\n\n'.join([f"- {t.get('filename')}{(' (' + t.get('dateGuess') + ')') if t.get('dateGuess') else ''}\n{slice_text(t.get('text'), 2000)}" for t in transcripts])
    gh = '\n'.join([f"- {c.get('date')} {c.get('author')}: {first_line(c.get('message'))} ({c.get('url')})" for c in github])
    def trello_block(c):
        comments = '\n'.join([f"  * {cm.get('date')} {cm.get('member')}: {cm.get('text')}" for cm in (c.get('comments') or [])])
        atts = '\n'.join([f"  * [{a.get('name')}]({a.get('url')})" for a in (c.get('attachments') or [])])
        return f"- {c.get('dateLastActivity')} {c.get('name')} ({c.get('url')})\n  Desc: {slice_text(c.get('desc'), 500)}\n" + (comments + '\n' if comments else '') + (atts + '\n' if atts else '')
    tr = '\n\n'.join([trello_block(c) for c in trello])
    return f"{header}\n\n== Transcripts ==\n{tx}\n\n== GitHub Commits ==\n{gh}\n\n== Trello Meeting Notes ==\n{tr}"

@app.route('/api/trello/board-actions', methods=['GET', 'POST', 'OPTIONS'])
def trello_board_actions():
    if request.method == 'OPTIONS':
        return make_response('', 204)
    if request.method == 'POST':
        data = request.get_json(force=True) or {}
        board_name = (data.get('boardName') or '').strip()
        since = (data.get('since') or '').strip()
        until = (data.get('until') or '').strip()
        types = (data.get('types') or '').strip()  # comma-separated action types or 'all'
    else:
        board_name = (request.args.get('boardName') or '').strip()
        since = (request.args.get('since') or '').strip()
        until = (request.args.get('until') or '').strip()
        types = (request.args.get('types') or '').strip()
    if not board_name or not since or not until:
        return jsonify({'error': 'Missing required params: boardName, since, until'}), 400

    try:
        boards = trello_get('https://api.trello.com/1/members/me/boards')
        board = next((b for b in boards if (b.get('name') or '').lower() == board_name.lower()), None)
        if not board:
            return jsonify({'error': f'Board not found: {board_name}'}), 404

        # Build Trello actions request
        params = {
            'limit': 1000,
            'since': since,
            'before': until,
        }
        if types and types.lower() != 'all':
            params['filter'] = types
        else:
            params['filter'] = 'all'

        actions = trello_get(f'https://api.trello.com/1/boards/{board.get("id")}/actions', params=params)

        def pick(a):
            data = a.get('data') or {}
            card = (data.get('card') or {}).get('name')
            list_name = (data.get('list') or {}).get('name') or ((data.get('listAfter') or {}) .get('name'))
            return {
                'date': a.get('date'),
                'type': a.get('type'),
                'member': (a.get('memberCreator') or {}).get('fullName'),
                'card': card,
                'list': list_name,
                'text': data.get('text'),
            }

        out = [pick(a) for a in (actions or [])]
        return jsonify({'actions': out})
    except requests.HTTPError as e:
        return jsonify({'error': 'Trello HTTP error', 'details': str(e)}), 502
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Unexpected trello error', 'details': str(e)}), 500

@app.route('/api/openai/summarize', methods=['POST', 'OPTIONS'])
def openai_summarize():
    if request.method == 'OPTIONS':
        return make_response('', 204)
    try:
        data = request.get_json(force=True) or {}
        system_prompt = (data.get('systemPrompt') or '').strip()
        input_obj = data.get('input') or {}
        if not system_prompt:
            return jsonify({'error': 'Missing systemPrompt'}), 400
        api_key = os.getenv('OPENAI_API_KEY', '').strip()
        if not api_key:
            return jsonify({'error': 'Missing OPENAI_API_KEY'}), 400
        user_content = build_user_content(input_obj)
        body = {
            'model': 'gpt-4o-mini',
            'messages': [
                { 'role': 'system', 'content': system_prompt },
                { 'role': 'user', 'content': user_content }
            ],
            'temperature': 0.2,
        }
        r = requests.post('https://api.openai.com/v1/chat/completions', json=body, headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }, timeout=60)
        if r.status_code >= 400:
            return jsonify({'error': f'OpenAI HTTP {r.status_code}', 'details': r.text}), r.status_code
        data = r.json()
        text = (((data.get('choices') or [{}])[0]).get('message') or {}).get('content') or ''
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': 'Unexpected openai error', 'details': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', '8000'))
    app.run(host='0.0.0.0', port=port)