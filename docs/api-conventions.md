# NEXORA API Conventions

## 1. Purpose

This document establishes the proposed communication standards
between the React frontend and Flask backend.

All developers must follow the agreed API conventions.

## 2. API Architecture

- React communicates with Flask using HTTP requests.
- JSON is the standard request and response format.
- Flask handles validation, authorization and business logic.
- PostgreSQL stores and retrieves application data.

## 3. Endpoint Naming

Proposed endpoint structure:

    /api/v1/resource

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

## 5. Standard Success Response

Proposed format:

    {
      "success": true,
      "message": "Request completed successfully",
      "data": {}
    }

## 6. Standard Error Response

Proposed format:

    {
      "success": false,
      "message": "Request failed",
      "errors": {
        "field": ["Validation error"]
      }
    }

Responses must not expose passwords, secrets,
database credentials or internal stack traces.

## 7. HTTP Status Codes

| Status | Meaning |
|---|---|
| 200 | Successful request |
| 201 | Resource created |
| 204 | Successful request with no response body |
| 400 | Invalid request |
| 401 | Authentication required |
| 403 | Permission denied |
| 404 | Resource not found |
| 409 | Resource conflict |
| 422 | Validation failure, if adopted |
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

The authentication mechanism is pending team agreement.

## 10. Financial API Rules

- Monetary values must use decimal-safe handling.
- Financial operations must use database transactions.
- Prevent duplicate financial operations where applicable.
- Use unique transaction references where required.
- Validate financial permissions before processing transactions.
- Never silently overwrite historical financial records.

## 11. Pagination and Filtering

Collection endpoints should support pagination.

Proposed query parameters:

    ?page=1&per_page=20

Filtering and sorting parameters must be documented
for each endpoint when introduced.

## 12. API Documentation and Testing

- Document every implemented endpoint.
- Include HTTP method and URL.
- Document required parameters and request bodies.
- Document successful responses and possible errors.
- Test endpoints before merging changes.
- Review API changes with affected frontend and backend developers.

## 13. Decisions Requiring Team Approval

- Whether API versioning will use /api/v1.
- Final authentication mechanism.
- Final response envelope.
- Pagination defaults and maximum page size.
- Whether HTTP 422 will be used for validation errors.
- Final endpoint naming and resource structure.

## 14. Approval

These conventions are proposed for team review.
They become the agreed API standard after team approval.
