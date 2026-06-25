"""Insight Recommender (Dispatcher) module configuration."""


class DispatcherConfig:
    dispatcher_timeout: int = 120
    dispatcher_max_iterations: int = 10
    sub_agent_timeout: int = 90
    sub_agent_max_iterations: int = 5
    max_concurrent_sub_agents: int = 5


_dispatcher_config = None


def get_dispatcher_config() -> DispatcherConfig:
    global _dispatcher_config
    if _dispatcher_config is None:
        _dispatcher_config = DispatcherConfig()
    return _dispatcher_config
