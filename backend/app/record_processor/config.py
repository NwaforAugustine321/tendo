from app.config.settings import settings


class RecordKnowledgeConfig:

    @property
    def max_entries(self) -> int:
        return settings.record_knowledge_max_entries

    @property
    def max_folder_entries(self) -> int:
        return settings.record_knowledge_max_folder_entries

    @property
    def max_summary_length(self) -> int:
        return settings.record_knowledge_max_summary_length

    @property
    def token_limit(self) -> int:
        return settings.record_knowledge_token_limit

    @property
    def max_retries(self) -> int:
        return settings.record_knowledge_max_retries

    @property
    def llm_timeout(self) -> int:
        return settings.record_knowledge_llm_timeout


_config: RecordKnowledgeConfig | None = None


def get_record_knowledge_config() -> RecordKnowledgeConfig:
    global _config
    if _config is None:
        _config = RecordKnowledgeConfig()
    return _config
