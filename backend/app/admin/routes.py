"""Admin report endpoints, scoped to one SACCO by the tenant guard."""

from datetime import date

from flask import jsonify, request

from app import admin_bp
from app.admin import reports
from app.models.membership import MembershipRole
from app.savings.accounts import list_sacco_accounts
from app.savings.history import page_params
from app.security.tenant import ADMIN_ONLY, sacco_scoped

REPORT_ROLES = (*ADMIN_ONLY, MembershipRole.STAFF)


def _date_param(name: str) -> date | None:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    return date.fromisoformat(raw)  # YYYY-MM-DD


@admin_bp.get("/saccos/<int:sacco_id>/reports/summary")
@sacco_scoped(REPORT_ROLES)
def sacco_summary(sacco_id: int):
    try:
        start, end = _date_param("from"), _date_param("to")
    except ValueError:
        return jsonify({"error": "Dates must look like 2026-01-31."}), 400
    if start and end and start > end:
        return jsonify({"error": "'from' must not be after 'to'."}), 400
    return jsonify(reports.sacco_summary(sacco_id, start, end))


@admin_bp.get("/saccos/<int:sacco_id>/reports/member-activity")
@sacco_scoped(REPORT_ROLES)
def member_activity(sacco_id: int):
    try:
        page, per_page = page_params()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(
        members=reports.member_activity(sacco_id, page, per_page),
        page=page,
        per_page=per_page,
    )


@admin_bp.get("/saccos/<int:sacco_id>/accounts")
@sacco_scoped(REPORT_ROLES)
def sacco_accounts(sacco_id: int):
    try:
        page, per_page = page_params()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    accounts, total = list_sacco_accounts(sacco_id, page, per_page)
    return jsonify(accounts=accounts, page=page, per_page=per_page, total=total)
