"""AI Business Understanding tools."""


def get_business_understanding(business_id: str, confidence_threshold: float = 0.0) -> dict:
    """Retrieve business understanding hypotheses above confidence threshold."""
    # TODO: implement via app.db.client
    return {"understandings": []}


def add_evidence(
    business_id: str,
    understanding_id: str,
    evidence_type: str,
    source_reference: dict,
    description: str,
) -> dict:
    """Add evidence observation to an understanding."""
    # TODO: implement
    return {"status": "added"}


def update_confidence(business_id: str, understanding_id: str, new_confidence: float, reason: str) -> dict:
    """Update confidence score for an understanding."""
    # TODO: implement
    return {"status": "updated", "confidence": new_confidence}


def evolve_understanding(business_id: str, action: str, data: dict) -> dict:
    """Create, merge, or retire business hypotheses."""
    # TODO: implement
    return {"status": action, "data": data}
