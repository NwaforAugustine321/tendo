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

    _tool.name = "save"
    return _tool


def search_business_knowledge(business_id: str, **_):
    @tool
    async def _tool(limit:int, query: str = "") -> str:
        """Search the business general knowledge. This gives overview of the business context understanding."""
        try:
            memory = Memory(scope=f"/insights/{business_id}")
            results = await memory.recall(query=query, limit=limit)
            if not results:
                return "No entries yet."
            entries = [{"content": m.content} for m in results]
            return json.dumps(entries, default=str)
        except Exception as e:
            logger.warning(f"search_business_knowledge failed: {e}")
            return "No entries yet."

    _tool.name = "search_information"
    return _tool


def business_knowledge_count(business_id: str, **_):
    @tool
    def _tool() -> str:
        """Get the total row count and column schema for this business's knowledge entries. Call this first to understand how much data is stored."""
        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(table_name="record_knowledge")
            if storage._table is None:
                return "No entries yet."

            scope_prefix = f"/{business_id}"
            df = storage._table.to_pandas()
            scoped = df[df["scope"].str.startswith(scope_prefix)]
            if len(scoped) == 0:
                return "No entries yet."
            return json.dumps({"total_rows": len(scoped)})
        except Exception as e:
            logger.warning(f"business_knowledge_count failed: {e}")
            return json.dumps({"error": str(e)})

    _tool.name = "count_rows"
    return _tool


def business_knowledge_paged_fetch(business_id: str, **_):
    @tool
    def _tool(pages: list[dict]) -> str:
        """Fetch multiple pages of knowledge entries for this business in parallel. Each page config must have 'limit' and 'offset' keys. Example: pages=[{"limit": n, "offset": n}, {"limit": n, "offset": n}]"""
        from concurrent.futures import ThreadPoolExecutor

        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(table_name="record_knowledge")
            if storage._table is None:
                return "No entries yet."

            scope_prefix = f"/{business_id}"
            df = storage._table.to_pandas()
            scoped = df[df["scope"].str.startswith(scope_prefix)].iloc[::-1].reset_index(drop=True)

            if len(scoped) == 0:
                return "No entries yet."

            def fetch_page(page):
                limit = page.get("limit", 2)
                offset = page.get("offset", 0)
                chunk = scoped.iloc[offset:offset + limit]
                records = []
                for _, row in chunk.iterrows():
                    content = str(row.get("content", ""))
                    if not content.strip():
                        continue
                    entry = {"content": content}
                    records.append(entry)
                return {"offset": offset, "limit": limit, "count": len(records), "entries": records}

            with ThreadPoolExecutor(max_workers=min(len(pages), 10)) as executor:
                all_results = list(executor.map(fetch_page, pages))

            return json.dumps(all_results, default=str)
        except Exception as e:
            logger.warning(f"business_knowledge_paged_fetch failed: {e}")
            return json.dumps({"error": str(e)})

    _tool.name = "fetch"
    return _tool


def search_record_knowledge(business_id: str, record_id: str, **_):
    from app.record_knowledge.record_agent import _get_record_storage

    @tool
    async def _tool(limit:int, query: str = "") -> str:
        """Search the record general knowledge. This gives overview of the record context understanding"""
        try:
            memory = Memory(scope=f"/{business_id}/{record_id}", storage=_get_record_storage())
            results = await memory.recall(query=query, limit=limit)
            if not results:
                return "No entries yet."
            entries = [{"content": m.content} for m in results]
            return json.dumps(entries, default=str)
        except Exception as e:
            logger.warning(f"search_record_knowledge failed: {e}")
            return "No entries yet."

    _tool.name = "search_information"
    return _tool


def record_knowledge_count(business_id: str, record_id: str, **_):
    @tool
    def _tool() -> str:
        """Get the total row count and column schema for this record's knowledge entries. Call this first to understand how much data is stored."""
        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(table_name="record_knowledge")
            if storage._table is None:
                return "No entries yet."

            scope_prefix = f"/{business_id}/{record_id}"
            df = storage._table.to_pandas()
            scoped = df[df["scope"].str.startswith(scope_prefix)]
            if len(scoped) == 0:
                return "No entries yet."
            return json.dumps({"total_rows": len(scoped)})
        except Exception as e:
            logger.warning(f"record_knowledge_count failed: {e}")
            return json.dumps({"error": str(e)})

    _tool.name = "count_row"
    return _tool


def record_knowledge_paged_fetch(business_id: str, record_id: str, **_):
    @tool
    def _tool(pages: list[dict]) -> str:
        """Fetch multiple pages of knowledge entries for this record in parallel. Each page config must have 'limit' and 'offset' keys. Example: pages=[{"limit": n, "offset": 0}, {"limit": n, "offset": n}]"""
        from concurrent.futures import ThreadPoolExecutor

        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(table_name="record_knowledge")
            if storage._table is None:
                return "No entries yet."

            scope_prefix = f"/{business_id}/{record_id}"
            df = storage._table.to_pandas()
            scoped = df[df["scope"].str.startswith(scope_prefix)].iloc[::-1].reset_index(drop=True)

            if len(scoped) == 0:
                return "No entries yet."

            def fetch_page(page):
                limit = page.get("limit", 2)
                offset = page.get("offset", 0)
                chunk = scoped.iloc[offset:offset + limit]
                records = []
                for _, row in chunk.iterrows():
                    content = str(row.get("content", ""))
                    if not content.strip():
                        continue
                    entry = {"content": content}
                    # Extract images from metadata_str if present
                    metadata_str = row.get("metadata_str", "")
                    if metadata_str:
                        try:
                            meta = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                            if isinstance(meta, dict):
                                # images may be in structured_metadata (JSON-encoded string within metadata)
                                structured = meta.get("structured_metadata", "")
                                if isinstance(structured, str) and structured:
                                    structured = json.loads(structured)
                                if isinstance(structured, dict) and "images" in structured:
                                    entry["images"] = structured["images"]
                        except (json.JSONDecodeError, TypeError):
                            pass
                    records.append(entry)
                return {"offset": offset, "limit": limit, "count": len(records), "entries": records}

            with ThreadPoolExecutor(max_workers=min(len(pages), 10)) as executor:
                all_results = list(executor.map(fetch_page, pages))

            return json.dumps(all_results, default=str)
        except Exception as e:
            logger.warning(f"record_knowledge_paged_fetch failed: {e}")
            return json.dumps({"error": str(e)})

    _tool.name = "fetch"
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
