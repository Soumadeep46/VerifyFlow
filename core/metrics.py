from __future__ import annotations
from core.models import Case, CaseState, ExceptionType

TAKE_RATE = 0.02
HOURS_IN_MONTH = 720


def estimated_revenue(case: Case, resolution_hours: float) -> float:
    if case.state in (CaseState.REJECTED, CaseState.ESCALATED):
        return 0.0
    if case.exception_type == ExceptionType.HARD_COMPLIANCE_BLOCK:
        return 0.0

    time_saved = max(case.baseline_hours - resolution_hours, 0.0)
    gmv = case.merchant.monthly_gmv
    return gmv * TAKE_RATE * (time_saved / HOURS_IN_MONTH) * case.confidence


def gmv_at_risk(cases: list[Case]) -> float:
    unresolved = (
        CaseState.RECEIVED,
        CaseState.PROCESSING,
        CaseState.NEEDS_EVIDENCE,
        CaseState.REVALIDATING,
        CaseState.READY_FOR_REVIEW,
        CaseState.ESCALATED,
    )
    return sum(c.merchant.monthly_gmv for c in cases if c.state in unresolved)


def resolution_hours(case: Case) -> float:
    if not case.resolved_at:
        return 0.0
    delta = case.resolved_at - case.created_at
    return delta.total_seconds() / 3600


def average_resolution_time(cases: list[Case]) -> float:
    resolved = [c for c in cases if c.resolved_at is not None]
    if not resolved:
        return 0.0
    total = sum(resolution_hours(c) for c in resolved)
    return total / len(resolved)


def confirmed_revenue_unlocked(cases: list[Case]) -> float:
    total = 0.0
    for c in cases:
        if c.state == CaseState.REVENUE_UNLOCKED and c.confidence >= 1.0:
            total += estimated_revenue(c, resolution_hours(c))
    return total


def total_estimated_revenue(cases: list[Case]) -> float:
    total = 0.0
    for c in cases:
        if c.resolved_at:
            total += estimated_revenue(c, resolution_hours(c))
    return total


def compliance_overrides(cases: list[Case]) -> int:
    count = 0
    for c in cases:
        if c.exception_type == ExceptionType.HARD_COMPLIANCE_BLOCK and c.state in (
            CaseState.APPROVED,
            CaseState.REVENUE_UNLOCKED,
        ):
            count += 1
    return count


def fifo_baseline_hours(cases: list[Case]) -> float:
    if not cases:
        return 0.0
    return sum(c.baseline_hours for c in cases) / len(cases)


def benchmark_summary(cases: list[Case]) -> dict:
    return {
        "fifo_baseline_avg_hours": fifo_baseline_hours(cases),
        "verifyflow_avg_hours": average_resolution_time(cases),
        "gmv_at_risk": gmv_at_risk(cases),
        "estimated_revenue_unlocked": total_estimated_revenue(cases),
        "confirmed_revenue_unlocked": confirmed_revenue_unlocked(cases),
        "compliance_overrides": compliance_overrides(cases),
    }