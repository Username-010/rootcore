"""Role hierarchy and permission checks."""

from __future__ import annotations

ROLE_RANK = {
    "viewer": 1,
    "member": 2,
    "admin": 3,
    "owner": 4,
}

VALID_ROLES = frozenset(ROLE_RANK)


def role_at_least(actual: str, minimum: str) -> bool:
    return ROLE_RANK.get(actual, 0) >= ROLE_RANK.get(minimum, 99)


def is_valid_role(role: str) -> bool:
    return role in VALID_ROLES


def can_manage_members(role: str) -> bool:
    return role_at_least(role, "admin")


def can_edit_household_settings(role: str) -> bool:
    return role == "owner"


def can_write_content(role: str) -> bool:
    return role_at_least(role, "member")
