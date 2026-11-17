"""Run the Thunder Client collection against a live API and check every request.

    python backend/scripts/check_collection.py [base_url] [run]

Reads docs/thunder/thunder-collection_NEXORA.json and the environment file next
to it, sends every request in order, applies the same checks Thunder Client
applies (status code, JSON values) and saves the same variables. Exit code 1
when any request does not return what the collection expects.

`run` is appended to every reference and the invited phone, so a second run on
the same database needs a new value (for example 02). Login allows 5 per minute
per address. When a login answers 429 the script waits out the minute once and
sends it again, and says so; a person clicking through in Thunder Client is
slower than that anyway.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

THUNDER = Path(__file__).resolve().parents[2] / "docs" / "thunder"
VAR = re.compile(r"\{\{(\w+)\}\}")


LIMIT_WAIT = 61  # login allows 5 per minute per address


def send(http) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(http, timeout=15) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        sys.exit(f"Cannot reach {http.full_url} ({exc.reason}). Is the API running?")


def lookup(data, path: str):
    """`json.a.b[0].c` -> data["a"]["b"][0]["c"], or None."""
    node = data
    for part in re.findall(r"[^.\[\]]+", path.removeprefix("json.")):
        try:
            node = node[int(part)] if part.isdigit() else node[part]
        except (KeyError, IndexError, TypeError):
            return None
    return node


def main() -> int:
    collection = json.loads((THUNDER / "thunder-collection_NEXORA.json").read_text())
    env_path = THUNDER / "thunder-environment_NEXORA-local.json"
    env_file = json.loads(env_path.read_text())
    env = {v["name"]: v["value"] for v in env_file["variables"]}
    if len(sys.argv) > 1:
        env["baseUrl"] = sys.argv[1].rstrip("/")
    if len(sys.argv) > 2:
        env["run"] = sys.argv[2]

    def fill(text: str) -> str:
        return VAR.sub(lambda m: str(env.get(m.group(1), m.group(0))), text)

    order = {f["_id"]: f["sortNum"] for f in collection["folders"]}
    names = {f["_id"]: f["name"] for f in collection["folders"]}
    requests = sorted(
        collection["requests"], key=lambda r: (order[r["containerId"]], r["sortNum"])
    )
    failures = 0
    folder = None
    for req in requests:
        if req["containerId"] != folder:
            folder = req["containerId"]
            print(f"\n{names[folder]}")
        body = fill(req["body"]["raw"]).encode() if req.get("body") else None
        http = urllib.request.Request(fill(req["url"]), data=body, method=req["method"])
        for header in req.get("headers", []):
            http.add_header(header["name"], fill(header["value"]))
        if req.get("auth", {}).get("type") == "bearer":
            http.add_header("Authorization", "Bearer " + fill(req["auth"]["bearer"]))
        status, raw = send(http)
        if status == 429 and req["url"].endswith("/auth/login"):
            print(f"  .... 429 on '{req['name']}': waiting {LIMIT_WAIT}s for the limit")
            time.sleep(LIMIT_WAIT)
            status, raw = send(http)
        try:
            data = json.loads(raw or b"null")
        except ValueError:
            data = None

        problems = []
        for test in req.get("tests", []):
            if test["type"] == "res-code" and str(status) != test["value"]:
                problems.append(f"status {status}, expected {test['value']}")
            elif test["type"] == "json-query":
                got = lookup(data, test["custom"])
                want = test["value"]
                if (got if isinstance(got, str) else json.dumps(got)) != want:
                    problems.append(f"{test['custom']} = {got!r}, expected {want}")
            elif test["type"] == "set-env-var":
                value = lookup(data, test["custom"])
                if value is not None:
                    env[test["value"].strip("{}")] = value
        mark = "PASS" if not problems else "FAIL"
        failures += bool(problems)
        print(f"  {mark} {status} {req['method']:<5} {req['name']}")
        for problem in problems:
            print(f"         {problem}; body: {json.dumps(data)[:200]}")

    total = len(requests)
    print(f"\n{total - failures}/{total} requests returned what the collection expects")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
