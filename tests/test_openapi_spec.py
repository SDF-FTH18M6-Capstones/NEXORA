"""docs/openapi.yaml lists every route (and nothing else)."""

import re
from pathlib import Path

SPEC = Path(__file__).resolve().parent.parent / "docs" / "openapi.yaml"


def test_the_spec_lists_every_route_and_nothing_else(app):
    in_spec = set(re.findall(r"^  (/api\S*):$", SPEC.read_text(), flags=re.M))
    in_code = {
        re.sub(r"<int:(\w+)>", r"{\1}", rule.rule)
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api")
    }
    assert in_spec == in_code
