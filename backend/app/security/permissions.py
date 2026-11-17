"""The permission catalogue and `can()` (Section 1, Neo).

This module is the interface the rest of the team builds against:

    can(user, sacco, permission, resource=None) -> bool

It answers from the database, not from a Python table: the membership's rows in
`membership_roles` decide which `roles` the caller holds, `role_permissions`
decides what those roles may do, and `platform_grants` decides platform access.
A membership that is not `active` is denied everything, including the
permissions its roles would otherwise grant.

The `PERMISSIONS` and `ROLE_PERMISSIONS` tables below are the catalogue: the
migration seeds the same data, `sync_catalogue()` writes it into a database that
was built with `create_all` (tests), and `tests/test_access_schema.py` fails if
the two ever disagree.

`resource` is accepted for object-level rules (a single loan, a single member)
that arrive with a later section. Until such a rule exists the answer is the
role-based one; callers may pass it now without changing their call shape.
"""

from dataclasses import dataclass

from sqlalchemy import select

from app.extensions import db
from app.models.access import (
    MembershipRoleLink,
    Permission,
    PlatformGrant,
    Role,
    RolePermission,
)
from app.models.membership import MembershipRole, MembershipStatus, SaccoMembership
from app.models.sacco import Sacco

# One entry per thing that may be allowed. `area.action`, lower case.
PERMISSIONS: dict[str, str] = {
    "sacco.view": "Read this SACCO's details",
    "sacco.manage": "Create, edit, activate or deactivate a SACCO",
    "member.view": "Read the SACCO's member list",
    "member.manage": "Add a member, invite a phone, change a role or status",
    "savings.view": "Read savings accounts and their history",
    "savings.post": "Post deposits, withdrawals, interest and fees",
    "savings.reverse": "Reverse a posted ledger entry",
    "loan.view": "Read loan requests and their decisions",
    "loan.request": "Request a loan",
    "loan.approve": "Approve or reject one step of a loan",
    "loan.disburse": "Disburse an approved loan",
    "loan.repay": "Repay a loan",
    "audit.view": "Read the audit trail",
    "dashboard.view": "See the dashboard for the caller's role",
}

# The five job titles, each with the permissions it holds. As in docs/schema.sql:
# a SACCO admin never approves loans and cannot read the audit log; the
# secretary is read-only and the only SACCO role that reads the audit log.
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "circle_admin": frozenset(
        {
            "sacco.view",
            "member.view",
            "member.manage",
            "savings.view",
            "savings.post",
            "savings.reverse",
            "loan.view",
            "dashboard.view",
        }
    ),
    "secretary": frozenset(
        {
            "sacco.view",
            "member.view",
            "savings.view",
            "loan.view",
            "audit.view",
            "dashboard.view",
        }
    ),
    "finance_officer": frozenset(
        {
            "sacco.view",
            "savings.view",
            "savings.post",
            "savings.reverse",
            "loan.view",
            "loan.disburse",
            "loan.repay",
            "dashboard.view",
        }
    ),
    "loans_officer": frozenset(
        {
            "sacco.view",
            "member.view",
            "savings.view",
            "loan.view",
            "loan.approve",
            "dashboard.view",
        }
    ),
    "member": frozenset(
        {
            "sacco.view",
            "savings.view",
            "loan.request",
            "loan.repay",
            "dashboard.view",
        }
    ),
}

# Never held by a SACCO admin membership, even through another title.
ADMIN_NEVER = frozenset({"loan.approve", "audit.view"})

ROLE_NAMES = {
    "circle_admin": "Circle administrator",
    "secretary": "Secretary",
    "finance_officer": "Finance officer",
    "loans_officer": "Loans officer",
    "member": "Member",
}

# Bridge for rows written before `membership_roles` existed (and for databases
# built with create_all, where the migration's backfill never ran).
LEGACY_ROLE_CODES = {
    MembershipRole.SACCO_ADMIN: "circle_admin",
    MembershipRole.STAFF: "secretary",
    MembershipRole.MEMBER: "member",
}


@dataclass(frozen=True)
class CatalogueWrite:
    roles: int
    permissions: int
    grants: int


def sync_catalogue(commit: bool = True) -> CatalogueWrite:
    """Insert the catalogue above into the database if it is missing.

    Idempotent: existing rows are left alone, which is what makes it safe on a
    database the migration already seeded.
    """
    role_rows = {role.code: role for role in db.session.execute(select(Role)).scalars()}
    permission_rows = {
        permission.code: permission
        for permission in db.session.execute(select(Permission)).scalars()
    }
    new_roles = 0
    new_permissions = 0

    for code, name in ROLE_NAMES.items():
        if code not in role_rows:
            role = Role(code=code, name=name)
            db.session.add(role)
            role_rows[code] = role
            new_roles += 1
    for code, description in PERMISSIONS.items():
        if code not in permission_rows:
            permission = Permission(code=code, description=description)
            db.session.add(permission)
            permission_rows[code] = permission
            new_permissions += 1
    db.session.flush()

    existing = {
        (link.role_id, link.permission_id)
        for link in db.session.execute(select(RolePermission)).scalars()
    }
    new_grants = 0
    for role_code, allowed in ROLE_PERMISSIONS.items():
        for permission_code in sorted(allowed):
            key = (role_rows[role_code].id, permission_rows[permission_code].id)
            if key not in existing:
                db.session.add(
                    RolePermission(role_id=key[0], permission_id=key[1])
                )
                existing.add(key)
                new_grants += 1

    if commit:
        db.session.commit()
    return CatalogueWrite(
        roles=new_roles, permissions=new_permissions, grants=new_grants
    )


def is_platform_owner(user) -> bool:
    """True when the user holds a platform grant (or the legacy owner flag)."""
    if user is None:
        return False
    if db.session.get(PlatformGrant, user.id) is not None:
        return True
    # Compatibility: platform owners that predate the grants table.
    return bool(getattr(user, "is_platform_owner", False))


def _membership_for(user_id: int, sacco_id: int) -> SaccoMembership | None:
    return db.session.execute(
        select(SaccoMembership).where(
            SaccoMembership.user_id == user_id,
            SaccoMembership.sacco_id == sacco_id,
        )
    ).scalar_one_or_none()


def _role_codes(membership: SaccoMembership) -> set[str]:
    codes = set(
        db.session.execute(
            select(Role.code)
            .join(MembershipRoleLink, MembershipRoleLink.role_id == Role.id)
            .where(MembershipRoleLink.membership_id == membership.id)
        ).scalars()
    )
    if codes:
        return codes
    legacy = LEGACY_ROLE_CODES.get(membership.role)
    return {legacy} if legacy else set()


def permissions_for(user, sacco) -> frozenset[str]:
    """Every permission the user holds in this SACCO, computed the same way.

    A platform owner holds all of them. Everyone else needs an active
    membership; a member of no SACCO holds none.
    """
    if user is None:
        return frozenset()
    if is_platform_owner(user):
        return frozenset(PERMISSIONS)
    sacco_id = sacco.id if isinstance(sacco, Sacco) else int(sacco)
    membership = _membership_for(user.id, sacco_id)
    if membership is None or membership.status is not MembershipStatus.ACTIVE:
        return frozenset()
    held = frozenset(
        db.session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .where(Role.code.in_(_role_codes(membership)))
        ).scalars()
    )
    if membership.role is MembershipRole.SACCO_ADMIN:
        # Agreed schema: a SACCO admin never approves loans and never reads the
        # audit log, whatever other titles the membership holds.
        held -= ADMIN_NEVER
    return held


def can(user, sacco, permission: str, resource=None) -> bool:  # noqa: ARG001
    """May `user` do `permission` in `sacco`?

    False for: no user, an unknown permission name, no membership, an inactive
    membership, a role that does not hold the permission, or a SACCO that does
    not match the membership. Platform owners hold every permission without a
    membership, which is what `platform_grants` exists for.
    """
    if user is None or permission not in PERMISSIONS:
        # An unknown name is a typo or a new permission nobody granted: deny.
        return False
    return permission in permissions_for(user, sacco)
