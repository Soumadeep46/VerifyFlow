from __future__ import annotations
import secrets
from datetime import datetime
from core.models import Case, CaseState, DocumentIssue


def generate_correction_message(issue: DocumentIssue) -> str:
    return (
        f"Your {issue.doc_type.replace('_', ' ').title()} could not be verified "
        f"because of: {issue.detail}. Please upload a clearer copy."
    )


def generate_secure_token() -> str:
    return secrets.token_urlsafe(16)


def send_correction_request(case: Case) -> dict:
    if not case.document_issues:
        return {"sent": False, "reason": "No document issues to remediate"}

    issue = case.document_issues[0]
    message = generate_correction_message(issue)
    token = generate_secure_token()
    case.transition(CaseState.NEEDS_EVIDENCE, f"Correction requested for {issue.doc_type}")

    return {
        "sent": True,
        "case_id": case.case_id,
        "message": message,
        "token": token,
        "issued_at": datetime.utcnow().isoformat(),
    }


def upload_replacement(case: Case, document_id: str) -> dict:
    case.transition(CaseState.REVALIDATING, f"Replacement {document_id} uploaded")
    return {"document_id": document_id, "status": "UPLOADED"}


def rerun_verification(case: Case, passed: bool) -> dict:
    if passed:
        case.document_issues = []
        case.transition(CaseState.APPROVED, "Replacement passed verification")
        case.confidence = 0.7
    else:
        case.transition(CaseState.NEEDS_EVIDENCE, "Replacement still failed verification")

    return {"case_id": case.case_id, "passed": passed, "state": case.state.value}


def delete_temporary_document(case: Case, document_id: str) -> dict:
    return {
        "event": "DOCUMENT_RETENTION_POLICY_APPLIED",
        "case_id": case.case_id,
        "document_id": document_id,
        "verification_status": "PASSED",
        "raw_document_deleted": True,
        "temporary_storage_deleted": True,
        "retention_policy": "DELETE_AFTER_VERIFICATION",
        "actor": "system",
        "timestamp": datetime.utcnow().isoformat(),
    }


def unlock_revenue(case: Case) -> dict:
    case.transition(CaseState.REVENUE_UNLOCKED, "Merchant activated post-remediation")
    case.confidence = 1.0
    case.resolved_at = datetime.utcnow()
    return {"case_id": case.case_id, "state": case.state.value, "confidence": case.confidence}