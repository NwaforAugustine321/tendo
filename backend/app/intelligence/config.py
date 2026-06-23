"""Intelligence module configuration."""

from app.config.settings import settings


class IntelligenceConfig:
    """Read intelligence config from app settings."""

    @property
    def llm_provider(self) -> str:
        return settings.intelligence_llm_provider

    @property
    def llm_model(self) -> str:
        return settings.intelligence_llm_model

    @property
    def max_iterations(self) -> int:
        return settings.intelligence_max_iterations

    @property
    def graph_db_uri(self) -> str:
        return settings.graph_db_uri

    @property
    def graph_db_user(self) -> str:
        return settings.graph_db_user

    @property
    def graph_db_password(self) -> str:
        return settings.graph_db_password

    @property
    def graph_db_name(self) -> str:
        return settings.graph_db_name

    @property
    def embedding_batch_size(self) -> int:
        return settings.intelligence_embedding_batch_size


_config = None


def get_intelligence_config() -> IntelligenceConfig:
    global _config
    if _config is None:
        _config = IntelligenceConfig()
    return _config
