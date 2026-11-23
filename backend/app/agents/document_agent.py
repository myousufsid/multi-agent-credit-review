"""
document_agent.py — Agent 3: Document Completeness Check (Stage 3).

Responsibility: Verify that all required supporting documents have been
received for the credit application. This agent checks document STATUS only —
it does not inspect, parse, or verify the actual content of any document,
and it does not perform OCR.

All findings are advisory and require qualified human review.
"""

from typing import Any

# Type alias for the structured output returned by this agent.
DocumentFindings = dict[str, Any]

# The set of document statuses this agent recognises.
_VALID_STATUSES = {"received", "missing", "pending"}

# The status value that marks a document as successfully submitted.
_RECEIVED_STATUS = "received"


def _validate_document_data(document_data: dict) -> None:
    """
    Raise ValueError if document_data is missing required keys or is malformed.
    """
    if "required_documents" not in document_data:
        raise ValueError(
            "document_data must contain a 'required_documents' list."
        )

    docs = document_data["required_documents"]
    if not isinstance(docs, list):
        raise ValueError(
            "document_data['required_documents'] must be a list."
        )

    for i, doc in enumerate(docs):
        if not isinstance(doc, dict):
            raise ValueError(
                f"document_data['required_documents'][{i}] must be a dict."
            )
        for required_key in ("name", "key", "status"):
            if required_key not in doc:
                raise ValueError(
                    f"Document entry at index {i} is missing required key '{required_key}'."
                )
        status = doc["status"]
        if status not in _VALID_STATUSES:
            raise ValueError(
                f"Document '{doc['name']}' has an unrecognised status '{status}'. "
                f"Expected one of: {sorted(_VALID_STATUSES)}."
            )


def run_document_agent(document_data: dict) -> DocumentFindings:
    """
    Check the completeness of the required document set for a credit application.

    Parameters
    ----------
    document_data : dict
        Structured document status data matching the sample_documents.json schema.

    Returns
    -------
    DocumentFindings
        A structured dictionary containing:
        - agent metadata (name, status)
        - received_documents: list of document names that have been received
        - missing_documents: list of document names that are still outstanding
        - is_complete: True only when every required document is received
        - findings: plain-language observations for the underwriter
        - unresolved_questions: items requiring follow-up action

    Raises
    ------
    ValueError
        If document_data is missing required keys, is malformed, or contains
        an unrecognised document status.
    """
    _validate_document_data(document_data)

    received: list[str] = []
    missing: list[str] = []

    for doc in document_data["required_documents"]:
        if doc["status"] == _RECEIVED_STATUS:
            received.append(doc["name"])
        else:
            # Treat both "missing" and "pending" as not yet received.
            missing.append(doc["name"])

    is_complete = len(missing) == 0

    findings: list[str] = []
    unresolved_questions: list[str] = []

    total = len(document_data["required_documents"])
    findings.append(
        f"{len(received)} of {total} required documents have been received."
    )

    if received:
        findings.append(
            "Received: " + ", ".join(f'"{d}"' for d in received) + "."
        )

    if missing:
        findings.append(
            "Missing: " + ", ".join(f'"{d}"' for d in missing) + ". "
            "The application cannot be fully assessed until all documents are received."
        )
        for doc_name in missing:
            unresolved_questions.append(
                f"When will \"{doc_name}\" be provided by the applicant?"
            )
    else:
        findings.append(
            "All required documents have been received. "
            "Document completeness does not block underwriter review."
        )

    return {
        "agent": "Document Agent",
        "status": "completed",
        "is_complete": is_complete,
        "received_documents": received,
        "missing_documents": missing,
        "findings": findings,
        "unresolved_questions": unresolved_questions,
    }
