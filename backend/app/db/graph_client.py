"""Business graph database async connection manager."""

import logging

from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)


class GraphClient:
    """Manages graph database driver lifecycle and provides transaction helpers."""

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        self._driver = None

    async def _get_driver(self):
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self._uri, auth=(self._user, self._password)
            )
        return self._driver

    async def execute_write(self, queries: list[tuple[str, dict]]) -> list[dict]:
        """Execute multiple queries in a single write transaction."""
        driver = await self._get_driver()
        async with driver.session(database=self._database) as session:
            results = []

            async def _work(tx):
                for query, params in queries:
                    result = await tx.run(query, params)
                    records = [record.data() async for record in result]
                    results.append(records)

            await session.execute_write(_work)
            return results

    async def execute_read(self, query: str, params: dict) -> list[dict]:
        """Execute a single read query."""
        driver = await self._get_driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(query, params)
            return [record.data() async for record in result]

    async def close(self):
        """Close the driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None


_client = None


def get_graph_client() -> GraphClient:
    """Get or create the singleton graph database client."""
    global _client
    if _client is None:
        from app.config.settings import settings

        _client = GraphClient(
            settings.graph_db_uri,
            settings.graph_db_user,
            settings.graph_db_password,
            settings.graph_db_name,
        )
    return _client
