class ContextLimitExceeded(
    RuntimeError,
):
    """
    The prompt cannot be reduced enough to fit
    within the model context window.
    """
