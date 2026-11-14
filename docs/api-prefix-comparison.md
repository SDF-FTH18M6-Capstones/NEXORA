# URL prefix: `/api/v1` or `/api`

**Decision needed from the team today.** It blocks Move 1 (Ryan's Blocker 4), and
every route written in Moves 2 to 4 inherits the answer.

## Where things stand

| Item | Current value |
|---|---|
| Blueprint mounts (`backend/app/__init__.py`) | `/auth`, `/saccos`, `/savings`, `/admin`, with no prefix |
| Health check | `/api/health` |
| `docs/api-conventions.md` | Proposes `/api/v1/resource`; line 139 lists versioning as undecided |
| `docs/architecture.md` and README smoke check | Refer to `/api/health` |
| Frontend | No API calls and no dev proxy yet, so nothing to migrate |
| Tests | `tests/test_auth_routes.py` hardcodes `/auth/...` in 5 places |

Whichever option wins, the blueprints, the health check and those 5 test paths change.

## Comparison

| | `/api/v1/...` | `/api/...` |
|---|---|---|
| Matches the existing docs | Yes. `api-conventions.md` already uses it. | No. The conventions doc must be rewritten. |
| Breaking changes later | A `/api/v2` can run beside v1 while the frontend migrates. | No clean path. The first breaking change forces a coordinated frontend and backend switch. |
| Health check | Moves to `/api/v1/health`, or stays at `/api/health` as an unversioned ops route (recommended). | Stays at `/api/health`, no change. |
| Effort now | Slightly more: one prefix constant plus a longer path in every request. | Slightly less. |
| Effort later | Low. Versioning exists already. | High if the API ever needs to break compatibility. |
| Risk for this project | Very low. Capstone with one client (our React app) and a short timeline. | Very low for the same reason. |

## How to mount it (either option)

Set the prefix once, in one place, so a later change is one line:

```python
API_PREFIX = "/api/v1"   # or "/api"

auth_bp   = Blueprint("auth",    __name__, url_prefix=f"{API_PREFIX}/auth")
saccos_bp = Blueprint("saccos",  __name__, url_prefix=f"{API_PREFIX}/saccos")
# same for savings_bp and admin_bp
```

Keep `/api/health` outside the versioned prefix. Load balancers and the README smoke
check shouldn't break when the API version changes.

## Recommendation: `/api/v1`

1. It is already written in `api-conventions.md`, so the docs need no rewrite.
2. Versioning costs one path segment now and avoids a forced migration later.
3. The frontend has no calls yet, so nothing needs migrating today.

The cost is small either way. The most important thing is to decide today and
record it in `docs/api-conventions.md`.

## Steps once the team decides (Ryan)

1. Agree the change to `backend/app/__init__.py` in the team chat first, because it
   is a shared file.
2. Apply the prefix to the four blueprints and decide whether `/api/health` stays
   unversioned.
3. Update the 5 hardcoded `/auth/...` paths in `tests/test_auth_routes.py`.
4. Update the README smoke check, `docs/architecture.md` and
   `docs/api-conventions.md` (replace "proposed" with "decided", and close the
   versioning question on line 139).
5. Run `pytest` from the repo root and confirm it passes.
6. Open the PR into `development`, ask for one approval, and wait for green CI.
