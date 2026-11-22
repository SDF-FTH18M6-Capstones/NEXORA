# NEXORA API Conventions

## 1. Purpose

This document establishes the communication standards
between the React frontend and Flask backend.

All developers must follow the agreed API conventions.

## 2. API Architecture

- React communicates with Flask using HTTP requests.
- JSON is the standard request and response format.
- Flask handles validation, authorization and business logic.
- PostgreSQL stores and retrieves application data.

## 3. Endpoint Naming

Endpoint structure (agreed by the team, Move 1):

    /api/v1/resource

Every resource route is served under `/api/v1`. The prefix is set in one
place, `API_PREFIX` in `backend/app/__init__.py`. The health check stays
unversioned at `GET /api/health`.

Examples:

    GET    /api/v1/saccos
    GET    /api/v1/saccos/<id>
    POST   /api/v1/saccos
    GET    /api/v1/members
    GET    /api/v1/members/<id>
    POST   /api/v1/members
    GET    /api/v1/transactions

Use:
- Lowercase resource names.
- Plural resource names.
- Consistent URL structures.
- Appropriate HTTP methods.

## 4. HTTP Methods

| Method | Purpose |
|---|---|
| GET | Retrieve resources |
| POST | Create resources or submit actions |
| PUT | Replace an existing resource |
| PATCH | Partially update a resource |
| DELETE | Delete a resource where permitted |

## 5. Success Responses

Success bodies are plain JSON with no envelope: the resource itself, or an
object such as `{"accounts": [...]}` or a page (`page`, `per_page`, and the
list). Creating something answers 201. A money route called again with a
`reference` it has already posted answers 200 with the original entry.

## 6. Error Responses

Every error, on every route, has this body:

    { "error": { "code": "not_found", "message": "Not found." } }

`code` is for programs and comes from the status. `message` is for people and
may be shown as is. Both are always present; there is nothing else in the body.
The helper is `error_response(status, message)` in `backend/app/errors.py`; no
route builds an error body by hand.

| Status | `code` |
|---|---|
| 400 | `validation_error` |
| 401 | `unauthorized` |
| 403 | `forbidden` |
| 404 | `not_found` |
| 405 | `method_not_allowed` |
| 409 | `conflict` |
| 413 | `payload_too_large` |
| 423 | `locked` (a locked account or a suspended SACCO) |
| 429 | `rate_limited` |
| 500 | `internal_error` |

Responses never expose passwords, secrets, database details or stack traces.

## 7. HTTP Status Codes

| Status | Meaning |
|---|---|
| 200 | Successful request, or a replayed money request |
| 201 | Resource created |
| 400 | Invalid request. **Every validation error is 400; the API never returns 422.** |
| 401 | Missing, invalid or expired token, or wrong credentials |
| 403 | Authenticated, but the role or membership does not allow it |
| 404 | Not found, **including another SACCO's record** (never 403, so ids cannot be probed) |
| 405 | Method not allowed |
| 409 | Conflicts with current state: duplicate email or name, reused reference, insufficient funds, reversing a reversal |
| 413 | Request body too large |
| 423 | Account locked after failed logins, or the SACCO is suspended |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

## 8. Request Validation

- Validate all incoming data in Flask.
- Validate required fields.
- Validate data types and formats.
- Reject invalid or unexpected values.
- Never trust frontend validation alone.
- Return clear validation errors.

## 9. Authentication and Authorization

- Protected endpoints require authentication.
- Flask verifies the authenticated user's identity.
- Flask checks permissions before executing protected actions.
- SACCO-level access restrictions must be enforced server-side.
- Authentication credentials must never be exposed in responses.

Authentication is a short-lived access token in the `Authorization: Bearer`
header plus a rotating refresh token (see `architecture.md`).

## 10. Financial API Rules

- Money is an integer in minor units (KES: 100 = 1.00). No floats, no decimals.
- Financial operations must use database transactions.
- Prevent duplicate financial operations where applicable.
- Use unique transaction references where required.
- Validate financial permissions before processing transactions.
- Never silently overwrite historical financial records.

## 11. Pagination and Filtering

Collection endpoints take `page` (from 1, default 1) and `per_page` (default
20, capped at 100). A value that is not a whole number, or is below 1, is a 400.
Filters are documented per endpoint in `openapi.yaml`.

## 12. API Documentation and Testing

- Document every implemented endpoint.
- Include HTTP method and URL.
- Document required parameters and request bodies.
- Document successful responses and possible errors.
- Test endpoints before merging changes.
- Review API changes with affected frontend and backend developers.

## 13. Approval

Agreed in Move 4. Change them only with the team.
