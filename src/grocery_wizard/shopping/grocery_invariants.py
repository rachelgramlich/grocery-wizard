"""Check grocery list output for whole-list quality (dedupe, sort, normalize idempotency)."""

from __future__ import annotations

from dataclasses import dataclass

from src.grocery_wizard.shopping.grocery_list import (
    _normalized_item_key,
    normalize_grocery_list_item,
)
from src.grocery_wizard.shopping.store_aisles import sort_grocery_items


@dataclass(frozen=True)
class GroceryInvariantViolation:
    code: str
    message: str


def check_grocery_list_invariants(lines: list[str]) -> list[GroceryInvariantViolation]:
    """Return violations for export lines (no bullets; same shape as ``final_items``)."""
    violations: list[GroceryInvariantViolation] = []
    cleaned = [line.strip() for line in lines if line.strip()]

    keys: dict[str, str] = {}
    for line in cleaned:
        key = _normalized_item_key(line)
        if key in keys:
            violations.append(
                GroceryInvariantViolation(
                    code="duplicate_key",
                    message=f"Duplicate item key {key!r}: {keys[key]!r} and {line!r}",
                )
            )
        else:
            keys[key] = line

    for line in cleaned:
        again = normalize_grocery_list_item(line)
        if again != line:
            violations.append(
                GroceryInvariantViolation(
                    code="not_idempotent",
                    message=f"Line is not idempotent under normalize_grocery_list_item: "
                    f"{line!r} → {again!r}",
                )
            )

    sorted_copy = sort_grocery_items(list(cleaned))
    if sorted_copy != cleaned:
        violations.append(
            GroceryInvariantViolation(
                code="not_aisle_sorted",
                message="List is not in store-aisle order (sort_grocery_items differs)",
            )
        )

    violations.extend(
        GroceryInvariantViolation(
            code="checklist_leak",
            message=f"Checklist markup leaked into export line: {line!r}",
        )
        for line in cleaned
        if "[ ]" in line or "[x]" in line.lower()
    )

    return violations


def assert_grocery_list_invariants(lines: list[str]) -> None:
    violations = check_grocery_list_invariants(lines)
    if violations:
        detail = "\n".join(f"- [{v.code}] {v.message}" for v in violations)
        raise AssertionError(f"Grocery list invariant violations:\n{detail}")
