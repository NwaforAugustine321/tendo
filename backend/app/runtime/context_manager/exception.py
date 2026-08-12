class ContextLimitExceeded(
    RuntimeError,
):
    """
    The prompt cannot be reduced enough to fit
    within the model context window.
    """


class ContextOptimizationFailed(
    RuntimeError,
):
    """
    The context optimization process failed —
    the prompt still exceeds the model context
    window after all strategies were exhausted.
    """
