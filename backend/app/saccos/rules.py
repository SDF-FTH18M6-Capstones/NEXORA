"""Circle rules: validation, publishing, acceptance and the loan checks.

The rules only record and enforce. Nothing here moves or lends money.
"""

import calendar
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.errors import (
    LOAN_OVER_CAP,
    LOAN_POOL_SHORT,
    LOAN_RULE_BROKEN,
    RULES_NOT_ACCEPTED,
)
from app.extensions import db
from app.models.loan import Loan, LoanRepayment, LoanStatus, SaccoSettings
from app.models.membership import MembershipStatus, SaccoMembership
from app.models.rules import CircleRules, RulesAcceptance
from app.models.sacco import Sacco
from app.models.savings import SavingsAccount
from app.savings.service import Conflict

FREQUENCIES = ("weekly", "twice_monthly", "monthly")
FREQUENCY_WORDS = {"weekly": "week", "twice_monthly": "half month", "monthly": "month"}
DEFAULT_LOAN_CAP_MULTIPLE = 3  # CARE VSLA manual: "up to but no more than 3x savings"
DEFAULT_CYCLE_MONTHS = 12
MAX_MONEY = 10**12  # minor units; far above any real circle, below BigInteger


def kes(minor: int) -> str:
    return f"KES {minor // 100:,}.{minor % 100:02d}"


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _clean_text(value, limit):
    if value is None or value == "":
        return None, None
    if not isinstance(value, str) or "\x00" in value:
        return None, "Send plain text."
    try:
        value.encode("utf-8")  # a lone surrogate would fail later, inside the database
    except UnicodeEncodeError:
        return None, "Send plain text."
    value = value.strip()
    if len(value) > limit:
        return None, f"Keep it to {limit} characters or fewer."
    return (value or None), None


def validate_rules(body) -> tuple[dict, dict]:
    """Return (values, errors). `errors` maps a field to a plain-words reason
    that says the format and gives an example; empty when everything is valid."""
    errors: dict[str, str] = {}
    values: dict = {}
    if not isinstance(body, dict):
        return {}, {"_": "Send the rules as a JSON object."}
    known = {
        "contribution_amount",
        "contribution_frequency",
        "loan_cap_multiple",
        "interest_percent",
        "repayment_period_value",
        "repayment_period_unit",
        "late_fine_amount",
        "cycle_months",
        "guarantors_required",
        "min_membership_days",
        "exit_rules",
        "loan_purposes",
    }
    extra = sorted(set(body) - known)
    if extra:
        errors["_"] = f"Unknown field(s): {', '.join(extra)}."

    def money(field, label, minimum, example):
        value = body.get(field)
        if not _is_int(value) or not minimum <= value <= MAX_MONEY:
            errors[field] = (
                f"{label} is required: a whole number of cents"
                f"{' above 0' if minimum else ', 0 or more'}. {example}"
            )
        else:
            values[field] = value

    money(
        "contribution_amount",
        "Contribution amount",
        1,
        "Example: 50000 means KES 500.00 each time.",
    )
    money(
        "late_fine_amount",
        "Late-payment fine",
        0,
        "Example: 5000 means KES 50.00. Send 0 for no fine.",
    )

    if body.get("contribution_frequency") in FREQUENCIES:
        values["contribution_frequency"] = body["contribution_frequency"]
    else:
        errors["contribution_frequency"] = (
            "Contribution frequency is required: weekly, twice_monthly or monthly."
        )

    multiple = body.get("loan_cap_multiple", DEFAULT_LOAN_CAP_MULTIPLE)
    if _is_int(multiple) and 1 <= multiple <= 10:
        values["loan_cap_multiple"] = multiple
    else:
        errors["loan_cap_multiple"] = (
            "Loan cap must be a whole number from 1 to 10: how many times a member's "
            "savings they may borrow. Example: 3 means savings of KES 1,000 allow up "
            "to KES 3,000. Left blank it is 3."
        )

    rate = body.get("interest_percent")
    try:
        if rate is None or isinstance(rate, bool | str):
            raise InvalidOperation
        rate = Decimal(str(rate))
        if not (Decimal(0) <= rate <= Decimal(100)) or rate != rate.quantize(
            Decimal("0.01")
        ):
            raise InvalidOperation
        values["interest_percent"] = rate
    except InvalidOperation:
        errors["interest_percent"] = (
            "Interest or service charge is required and has no default: type the "
            "percentage your circle agreed to charge per loan, from 0 to 100 with up "
            "to 2 decimals. Example: 10 means 10% of each loan. Type 0 if loans "
            "carry no charge."
        )

    unit = body.get("repayment_period_unit")
    period = body.get("repayment_period_value")
    limit = {"days": 730, "months": 24}.get(unit) if isinstance(unit, str) else None
    if limit and _is_int(period) and 1 <= period <= limit:
        values["repayment_period_value"] = period
        values["repayment_period_unit"] = unit
    else:
        errors["repayment_period_value"] = (
            "Repayment period is required: a whole number with a unit of days "
            "(1 to 730) or months (1 to 24). Example: 6 months."
        )

    months = body.get("cycle_months", DEFAULT_CYCLE_MONTHS)
    if _is_int(months) and 9 <= months <= 12:
        values["cycle_months"] = months
    else:
        errors["cycle_months"] = (
            "Cycle length must be 9 to 12 months. Example: 12. Left blank it is 12."
        )

    for field, label, high, example in (
        (
            "guarantors_required",
            "Guarantors required",
            10,
            "Example: 2. Send 0 for none.",
        ),
        (
            "min_membership_days",
            "Minimum membership before borrowing",
            730,
            "A whole number of days. Example: 90. Send 0 for none.",
        ),
    ):
        value = body.get(field, 0)
        if _is_int(value) and 0 <= value <= high:
            values[field] = value
        else:
            errors[field] = (
                f"{label} must be a whole number from 0 to {high}. {example}"
            )

    for field, label, limit_chars in (
        ("exit_rules", "Exit rules", 500),
        ("loan_purposes", "Allowed loan purposes", 200),
    ):
        text, problem = _clean_text(body.get(field), limit_chars)
        if problem:
            errors[field] = (
                f"{label}: {problem} Example: school fees, stock, medical bills."
            )
        else:
            values[field] = text
    return values, errors


def add_months(day: date, months: int) -> date:
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def today() -> date:
    return datetime.now(UTC).date()


PROPOSAL_DAYS = 30


def proposal_expired(proposal) -> bool:
    return proposal.created_at < datetime.now(UTC) - timedelta(days=PROPOSAL_DAYS)


def lock_sacco(sacco_id: int) -> None:
    """Serialise rule changes and loan checks for one circle."""
    db.session.execute(select(Sacco.id).where(Sacco.id == sacco_id).with_for_update())


def electorate(sacco_id: int, rules_id: int) -> list[int]:
    """Active members who accepted the current rules: the people who may vote."""
    return list(
        db.session.execute(
            select(SaccoMembership.id)
            .join(RulesAcceptance, RulesAcceptance.membership_id == SaccoMembership.id)
            .where(
                SaccoMembership.sacco_id == sacco_id,
                SaccoMembership.status == MembershipStatus.ACTIVE,
                RulesAcceptance.rules_id == rules_id,
            )
            .order_by(SaccoMembership.id)
        ).scalars()
    )


def active_member_count(sacco_id: int) -> int:
    return db.session.scalar(
        select(func.count())
        .select_from(SaccoMembership)
        .where(
            SaccoMembership.sacco_id == sacco_id,
            SaccoMembership.status == MembershipStatus.ACTIVE,
        )
    )


def can_still_pass(voters: int, rejections: int, active: int) -> bool:
    """A change needs more than half of ALL active members at proposal time, so
    members who did not accept the current rules count against it."""
    return (voters - rejections) * 2 > active


def current_rules(sacco_id: int) -> CircleRules | None:
    return db.session.execute(
        select(CircleRules)
        .where(CircleRules.sacco_id == sacco_id)
        .order_by(CircleRules.version.desc())
        .limit(1)
    ).scalar_one_or_none()


def lock_message(rules: CircleRules) -> str:
    if today() < rules.cycle_ends_on:
        return (
            f"These rules are locked until the cycle ends on "
            f"{rules.cycle_ends_on:%d %b %Y}. "
            "They can change only after that, by a vote of the members."
        )
    return "This circle already has rules. Propose a change and the members vote on it."


def publish_rules(sacco_id: int, values: dict, user_id: int | None) -> CircleRules:
    """Add the next version and start its cycle today. The caller checked it may."""
    current = current_rules(sacco_id)
    start = today()
    row = CircleRules(
        sacco_id=sacco_id,
        version=current.version + 1 if current else 1,
        cycle_starts_on=start,
        cycle_ends_on=add_months(start, values["cycle_months"]),
        created_by_user_id=user_id,
        **values,
    )
    db.session.add(row)
    db.session.flush()
    if current is not None:
        # Members who accepted the last version stay accepted, so adopting a new
        # version does not stop every one of them from borrowing until they all
        # open the app again. They can still read it and vote on the next change.
        db.session.execute(
            pg_insert(RulesAcceptance)
            .from_select(
                ["membership_id", "rules_id"],
                select(RulesAcceptance.membership_id, literal(row.id)).where(
                    RulesAcceptance.rules_id == current.id
                ),
            )
            .on_conflict_do_nothing()
        )
    # One source of truth: the loan service reads the multiple from the settings
    # row when a circle has none, so keep that row in step.
    settings = db.session.get(SaccoSettings, sacco_id)
    if settings is None:
        db.session.add(
            SaccoSettings(
                sacco_id=sacco_id, savings_multiple=values["loan_cap_multiple"]
            )
        )
    else:
        settings.savings_multiple = values["loan_cap_multiple"]
    return row


def has_accepted(membership_id: int, rules_id: int) -> bool:
    return db.session.get(RulesAcceptance, (membership_id, rules_id)) is not None


def accept(membership_id: int, rules_id: int) -> None:
    db.session.execute(
        pg_insert(RulesAcceptance)
        .values(membership_id=membership_id, rules_id=rules_id)
        .on_conflict_do_nothing()
    )


def rules_json(rules: CircleRules | None, accepted: bool | None = None) -> dict | None:
    if rules is None:
        return None
    return {
        "id": rules.id,
        "version": rules.version,
        "contribution_amount": rules.contribution_amount,
        "contribution_frequency": rules.contribution_frequency,
        "loan_cap_multiple": rules.loan_cap_multiple,
        "interest_percent": float(rules.interest_percent),
        "repayment_period_value": rules.repayment_period_value,
        "repayment_period_unit": rules.repayment_period_unit,
        "late_fine_amount": rules.late_fine_amount,
        "cycle_months": rules.cycle_months,
        "guarantors_required": rules.guarantors_required,
        "min_membership_days": rules.min_membership_days,
        "exit_rules": rules.exit_rules,
        "loan_purposes": rules.loan_purposes,
        "cycle_starts_on": rules.cycle_starts_on.isoformat(),
        "cycle_ends_on": rules.cycle_ends_on.isoformat(),
        "locked": today() < rules.cycle_ends_on,
        "accepted": accepted,
    }


def pool_cash(sacco_id: int) -> int:
    """Cash the circle can still lend, on the cautious side.

    A disbursed loan is credited to the borrower's account, so it is inside the
    balances total and has also left the pool: it is taken off twice. Loans still
    waiting for approval or payout are reserved so two requests cannot both claim
    the same cash. If a borrower withdrew the proceeds this can understate the
    pool, which only ever makes the circle refuse a loan it could have made.
    """
    total = db.session.scalar(
        select(func.coalesce(func.sum(SavingsAccount.balance), 0)).where(
            SavingsAccount.sacco_id == sacco_id
        )
    )
    lent = db.session.scalar(
        select(func.coalesce(func.sum(Loan.principal), 0)).where(
            Loan.sacco_id == sacco_id, Loan.status == LoanStatus.DISBURSED
        )
    )
    paid = db.session.scalar(
        select(func.coalesce(func.sum(LoanRepayment.amount), 0))
        .join(Loan, Loan.id == LoanRepayment.loan_id)
        .where(Loan.sacco_id == sacco_id, Loan.status == LoanStatus.DISBURSED)
    )
    reserved = db.session.scalar(
        select(func.coalesce(func.sum(Loan.principal), 0)).where(
            Loan.sacco_id == sacco_id,
            Loan.status.in_((LoanStatus.REQUESTED, LoanStatus.APPROVED)),
        )
    )
    outstanding = int(lent) - int(paid)
    return int(total) - 2 * outstanding - int(reserved)


def check_loan_request(membership, savings: int, principal: int, term_months) -> None:
    """Refuse a loan that breaks the circle's rules, in plain words.
    A circle without published rules is not checked."""
    rules = current_rules(membership.sacco_id)
    if rules is None:
        return
    lock_sacco(membership.sacco_id)  # two requests cannot both spend the same pool
    if not has_accepted(membership.id, rules.id):
        raise Conflict(
            "Read and accept your circle's rules before asking for a loan.",
            code=RULES_NOT_ACCEPTED,
        )
    # Member since: when they first accepted the rules (at joining), not when they
    # were invited; an invitation can sit unused for months.
    first = db.session.scalar(
        select(func.min(RulesAcceptance.accepted_at)).where(
            RulesAcceptance.membership_id == membership.id
        )
    )
    joined = (first or membership.created_at).astimezone(UTC).date()
    waited = (today() - joined).days
    if waited < rules.min_membership_days:
        ready = joined.toordinal() + rules.min_membership_days
        raise Conflict(
            f"This circle lets members borrow after {rules.min_membership_days} days. "
            f"You have been a member for {waited}. You can ask from "
            f"{date.fromordinal(ready):%d %b %Y}.",
            code=LOAN_RULE_BROKEN,
        )
    days = rules.repayment_period_value * (
        30 if rules.repayment_period_unit == "months" else 1
    )
    if term_months is not None and term_months * 30 > days:
        raise Conflict(
            f"This circle's loans must be repaid within {rules.repayment_period_value} "
            f"{rules.repayment_period_unit}. You asked for {term_months} months.",
            code=LOAN_RULE_BROKEN,
        )
    most = rules.loan_cap_multiple * savings
    if principal > most:
        raise Conflict(
            f"You can borrow up to {rules.loan_cap_multiple} times your savings. Your "
            f"savings are {kes(savings)}, so the most is {kes(most)}. "
            f"You asked for {kes(principal)}.",
            code=LOAN_OVER_CAP,
        )
    pool = pool_cash(membership.sacco_id)
    if principal > pool:
        raise Conflict(
            f"The circle does not have enough cash for this loan right now. It holds "
            f"{kes(max(pool, 0))} and you asked for {kes(principal)}. "
            "Ask for less, or try "
            "again after more contributions come in.",
            code=LOAN_POOL_SHORT,
        )
