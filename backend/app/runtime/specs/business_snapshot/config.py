"""Business Snapshot module configuration."""


class SnapshotConfig:
    """Snapshot generation config."""

    @property
    def max_iterations(self) -> int:
        """Max agent iterations (tool calls) for snapshot generation."""
        return 20


_config = None


def get_snapshot_config() -> SnapshotConfig:
    global _config
    if _config is None:
        _config = SnapshotConfig()
    return _config
