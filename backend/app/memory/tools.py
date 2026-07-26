import json
import logging
from langchain_core.tools import tool
from app.memory.memory import Memory

logger = logging.getLogger(__name__)

def save_to_business_memory(business_id: str, **_):
    @tool
    async def _tool(contents: list[str]) -> str:
        """Store one or more important business facts, decisions, observations, or lessons in memory so they can be recalled later. Pass multiple items at once when you have several things worth remembering."""
        if not contents:
            return "No items provided to save."
        try:
            memory = Memory(scope=f"/business/{business_id}")
            await memory.remember_many(contents)
            return f"Saved {len(contents)} item(s) to business memory."
        except Exception as e:
            logger.warning(f"save_to_business_memory failed: {e}")
            return f"Could not save to memory: {e}"

    _tool.name = "save_to_business_memory"
    return _tool


def search_business_knowledge(business_id: str, **_):
    @tool
    async def _tool(query: str = "", limit: int = 30) -> str:
        """Search the business general knowledge. This gives overview of the business context understanding."""
        try:
            memory = Memory(scope=f"/insights/{business_id}")
            results = await memory.recall(query=query, limit=limit)
            entries = [{"summary": m.content} for m in results]
            return json.dumps(entries, default=str)
        except Exception as e:
            logger.warning(f"search_business_knowledge failed: {e}")
            return json.dumps([])

    _tool.name = "search_business_knowledge"
    return _tool


def business_knowledge_count(business_id: str, **_):
    @tool
    def _tool() -> str:
        """Get the total row count and column schema for this business's knowledge entries. Call this first to understand how much data is stored."""
        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(table_name="record_knowledge")
            if storage._table is None:
                return json.dumps({"total_rows": 0, "columns": []})

            scope_prefix = f"/{business_id}"
            df = storage._table.to_pandas()
            scoped = df[df["scope"].str.startswith(scope_prefix)]
            columns = [field.name for field in storage._table.schema]
            return json.dumps({"total_rows": len(scoped), "columns": columns, "scope": scope_prefix})
        except Exception as e:
            logger.warning(f"business_knowledge_count failed: {e}")
            return json.dumps({"error": str(e)})

    _tool.name = "business_knowledge_count"
    return _tool


def business_knowledge_paged_fetch(business_id: str, **_):
    @tool
    def _tool(pages: list[dict]) -> str:
        """Fetch multiple pages of knowledge entries for this business. Each page config must have 'limit' and 'offset' keys. Example: pages=[{"limit": 50, "offset": 0}, {"limit": 50, "offset": 50}]"""
        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(table_name="record_knowledge")
            if storage._table is None:
                return json.dumps([])

            scope_prefix = f"/{business_id}"
            df = storage._table.to_pandas()
            scoped = df[df["scope"].str.startswith(scope_prefix)].reset_index(drop=True)

            all_results = []
            for page in pages:
                limit = page.get("limit", 50)
                offset = page.get("offset", 0)
                chunk = scoped.iloc[offset:offset + limit]
                records = []
                for _, row in chunk.iterrows():
                    records.append({
                        "id": str(row.get("id", "")),
                        "content": str(row.get("content", "")),
                        "scope": str(row.get("scope", "")),
                        "importance": float(row.get("importance", 0.5)),
                        "source": str(row.get("source", "")),
                        "created_at": str(row.get("created_at", "")),
                    })
                all_results.append({"offset": offset, "limit": limit, "count": len(records), "records": records})

            return json.dumps(all_results, default=str)
        except Exception as e:
            logger.warning(f"business_knowledge_paged_fetch failed: {e}")
            return json.dumps({"error": str(e)})

    _tool.name = "business_knowledge_paged_fetch"
    return _tool


def search_record_knowledge(business_id: str, record_id: str, **_):
    from app.record_knowledge.record_agent import _get_record_storage

    @tool
    async def _tool(query: str = "", limit: int = 10) -> str:
        """Search the record general knowledge. This gives overview of the record context understanding"""
        try:
            memory = Memory(scope=f"/{business_id}/{record_id}", storage=_get_record_storage())
            results = await memory.recall(query=query, limit=limit)
            entries = [{"summary": m.content, "type": (m.metadata or {}).get("content_type", "")} for m in results]
            return json.dumps(entries, default=str)
        except Exception as e:
            logger.warning(f"search_record_knowledge failed: {e}")
            return json.dumps([])

    _tool.name = "search_record_knowledge"
    return _tool


def record_knowledge_count(business_id: str, record_id: str, **_):
    @tool
    def _tool() -> str:
        """Get the total row count and column schema for this record's knowledge entries. Call this first to understand how much data is stored."""
        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(table_name="record_knowledge")
            if storage._table is None:
                return json.dumps({"total_rows": 0, "columns": []})

            scope_prefix = f"/{business_id}/{record_id}"
            df = storage._table.to_pandas()
            scoped = df[df["scope"].str.startswith(scope_prefix)]
            columns = [field.name for field in storage._table.schema]
            return json.dumps({"total_rows": len(scoped), "columns": columns, "scope": scope_prefix})
        except Exception as e:
            logger.warning(f"record_knowledge_count failed: {e}")
            return json.dumps({"error": str(e)})

    _tool.name = "record_knowledge_count"
    return _tool


def record_knowledge_paged_fetch(business_id: str, record_id: str, **_):
    @tool
    def _tool(pages: list[dict]) -> str:
        """Fetch multiple pages of knowledge entries for this record. Each page config must have 'limit' and 'offset' keys. Example: pages=[{"limit": 50, "offset": 0}, {"limit": 50, "offset": 50}]"""
        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(table_name="record_knowledge")
            if storage._table is None:
                return json.dumps([])

            scope_prefix = f"/{business_id}/{record_id}"
            df = storage._table.to_pandas()
            scoped = df[df["scope"].str.startswith(scope_prefix)].reset_index(drop=True)

            all_results = []
            for page in pages:
                limit = page.get("limit", 50)
                offset = page.get("offset", 0)
                chunk = scoped.iloc[offset:offset + limit]
                records = []
                for _, row in chunk.iterrows():
                    records.append({
                        "id": str(row.get("id", "")),
                        "content": str(row.get("content", "")),
                        "scope": str(row.get("scope", "")),
                        "importance": float(row.get("importance", 0.5)),
                        "source": str(row.get("source", "")),
                        "created_at": str(row.get("created_at", "")),
                    })
                all_results.append({"offset": offset, "limit": limit, "count": len(records), "records": records})

            return json.dumps(all_results, default=str)
        except Exception as e:
            logger.warning(f"record_knowledge_paged_fetch failed: {e}")
            return json.dumps({"error": str(e)})

    _tool.name = "record_knowledge_paged_fetch"
    return _tool


def get_record_knowledge_tools(business_id: str, record_id: str) -> list:
    """Get record-scoped knowledge tools."""
    return [
        search_record_knowledge(business_id=business_id, record_id=record_id),
        record_knowledge_count(business_id=business_id, record_id=record_id),
        record_knowledge_paged_fetch(business_id=business_id, record_id=record_id),
    ]


def get_business_memory_tools(business_id: str) -> list:
    """Get business-scoped memory tools."""
    return [
        save_to_business_memory(business_id=business_id),
        search_business_knowledge(business_id=business_id),
        business_knowledge_count(business_id=business_id),
        business_knowledge_paged_fetch(business_id=business_id),
    ]
