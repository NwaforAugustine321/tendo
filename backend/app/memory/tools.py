import json
import logging
from langchain_core.tools import tool
from app.memory.memory import Memory

logger = logging.getLogger(__name__)


def save_knowledge(business_id: str, scopes: list[str] | None = None, **_):
    @tool
    async def _tool(contents: list[str]) -> str:
        """Store one or more important facts, decisions, observations, or lessons in memory so they can be recalled later."""
        if not contents:
            return "No items provided to save."
        try:
            write_scopes = scopes or [f"/business/{business_id}"]
            memory = Memory(scopes=write_scopes, business_id=business_id)
            await memory.remember_many(contents)
            return f"Saved {len(contents)} item(s) to memory."
        except Exception as e:
            logger.warning(f"save_knowledge failed: {e}")
            return f"Could not save to memory: {e}"

    _tool.name = "save_knowledge"
    return _tool


def search_knowledge(business_id: str, scopes: list[str] | None = None, **_):
    @tool
    async def _tool(limit: int, query: str = "") -> str:
        """Search knowledge for context and understanding. Returns relevant entries matching the query."""
        try:
            memory = Memory(scopes=scopes or ["/"], business_id=business_id)
            results = await memory.recall(query=query, limit=limit)
            if not results:
                return "No entries yet."
            entries = []
            for m in results:
                entry = {"content": m.content}
                if m.images:
                    entry["images"] = m.images
                if m.audio:
                    entry["audio"] = m.audio
                if m.videos:
                    entry["videos"] = m.videos
                entries.append(entry)
            return json.dumps(entries, default=str)
        except Exception as e:
            logger.warning(f"search_knowledge failed: {e}")
            return "No entries yet."

    _tool.name = "search_knowledge"
    return _tool


def count_knowledge(business_id: str, scopes: list[str] | None = None, **_):
    @tool
    def _tool() -> str:
        """Get the total row count for knowledge entries."""
        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(business_id=business_id)
            if storage._table is None:
                return "No entries yet."

            df = storage._table.to_pandas()
            if scopes:
                mask = None
                for s in scopes:
                    scope_mask = df["scope"].str.startswith(s)
                    mask = scope_mask if mask is None else (mask | scope_mask)
                scoped = df[mask] if mask is not None else df
            else:
                scoped = df

            if len(scoped) == 0:
                return "No entries yet."
            return json.dumps({"total_rows": len(scoped)})
        except Exception as e:
            logger.warning(f"count_knowledge failed: {e}")
            return json.dumps({"error": str(e)})

    _tool.name = "count_knowledge"
    return _tool


def fetch_knowledge(business_id: str, scopes: list[str] | None = None, **_):
    @tool
    def _tool(pages: list[dict]) -> str:
        """Fetch multiple pages of knowledge entries in parallel. Each page config must have 'limit' and 'offset' keys."""
        from concurrent.futures import ThreadPoolExecutor

        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(business_id=business_id)
            if storage._table is None:
                return "No entries yet."

            df = storage._table.to_pandas()
            if scopes:
                mask = None
                for s in scopes:
                    scope_mask = df["scope"].str.startswith(s)
                    mask = scope_mask if mask is None else (mask | scope_mask)
                scoped = df[mask].iloc[::-1].reset_index(drop=True) if mask is not None else df.iloc[::-1].reset_index(drop=True)
            else:
                scoped = df.iloc[::-1].reset_index(drop=True)

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
                    images = row.get("images")
                    if images is not None and isinstance(images, list) and len(images) > 0:
                        decoded = []
                        for img in images:
                            if isinstance(img, bytes):
                                decoded.append(img.decode("utf-8", errors="replace"))
                            elif isinstance(img, str):
                                decoded.append(img)
                        if decoded:
                            entry["images"] = decoded
                    records.append(entry)
                return {"offset": offset, "limit": limit, "count": len(records), "entries": records}

            with ThreadPoolExecutor(max_workers=min(len(pages), 10)) as executor:
                all_results = list(executor.map(fetch_page, pages))

            return json.dumps(all_results, default=str)
        except Exception as e:
            logger.warning(f"fetch_knowledge failed: {e}")
            return json.dumps({"error": str(e)})

    _tool.name = "fetch_knowledge"
    return _tool


def get_knowledge_tools(business_id: str, scopes: list[str] | None = None) -> list:
    return [
        save_knowledge(business_id=business_id, scopes=scopes),
        search_knowledge(business_id=business_id, scopes=scopes),
        count_knowledge(business_id=business_id, scopes=scopes),
        fetch_knowledge(business_id=business_id, scopes=scopes),
    ]
