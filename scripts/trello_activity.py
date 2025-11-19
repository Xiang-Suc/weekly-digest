import os
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


def trello_get(url: str, qp: dict) -> dict:
    key = os.environ.get("TRELLO_KEY")
    token = os.environ.get("TRELLO_TOKEN")
    if not key or not token:
        raise RuntimeError("Missing TRELLO_KEY/TRELLO_TOKEN")
    qp = dict(qp or {})
    qp.update({"key": key, "token": token})
    full = url + "?" + urllib.parse.urlencode(qp)
    with urllib.request.urlopen(full, timeout=60) as r:
        return json.loads(r.read())


def iso_week_range(now_utc: datetime):
    monday = (now_utc - timedelta(days=now_utc.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    next_monday = monday + timedelta(days=7)
    since = monday.isoformat().replace("+00:00", "Z")
    before = next_monday.isoformat().replace("+00:00", "Z")
    return since, before


def summarize_actions(actions: list) -> dict:
    by_type = {}
    for a in actions:
        t = a.get("type") or "unknown"
        by_type[t] = by_type.get(t, 0) + 1

    def pick(a):
        data = a.get("data") or {}
        card = (data.get("card") or {}).get("name")
        text = data.get("text")
        list_name = (data.get("list") or {}).get("name") or (
            (data.get("listAfter") or {}).get("name")
        )
        return {
            "date": a.get("date"),
            "type": a.get("type"),
            "member": (a.get("memberCreator") or {}).get("fullName"),
            "card": card,
            "list": list_name,
            "text": text,
        }

    return {
        "total": len(actions),
        "byType": by_type,
        "sample": [pick(x) for x in actions[:10]],
    }


def main():
    now = datetime.now(timezone.utc)
    since, before = iso_week_range(now)

    boards = trello_get("https://api.trello.com/1/members/me/boards", {"fields": "name"})
    board = next((b for b in boards if (b.get("name") or "") == "Zcash Me"), None)
    if not board:
        raise RuntimeError("Board not found: Zcash Me")

    bid = board.get("id")
    actions = trello_get(
        f"https://api.trello.com/1/boards/{bid}/actions",
        {"filter": "all", "limit": 1000, "since": since, "before": before},
    )

    summary = summarize_actions(actions)
    print(json.dumps({"range": {"since": since, "before": before}, **summary}, indent=2))


if __name__ == "__main__":
    main()