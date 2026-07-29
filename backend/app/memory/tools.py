import json
import logging
from langchain_core.tools import tool
from app.memory.memory import Memory
from pydantic import BaseModel
from typing import TypedDict

class Page(BaseModel):
    limit: int
    offset: int

logger = logging.getLogger(__name__)

def save_knowledge(business_id: str, scopes: list[str] | None = None, **_):
    @tool
    async def _tool(contents: list[str]) -> dict:
        """Store one or more important facts, decisions, observations, or lessons in memory so they can be recalled later."""
        if not contents:
            return {"content": "No items provided to save.", "metadata": {}, "images": [], "videos": [], "audios": []}
        try:
            write_scopes = scopes or [f"/business/{business_id}"]
            memory = Memory(scopes=write_scopes, business_id=business_id)
            await memory.remember_many(contents)
            return {
                "content": f"Saved {len(contents)} item(s) to memory.",
                "metadata": {"count": len(contents)},
                "images": [],
                "videos": [],
                "audios": [],
            }
        except Exception as e:
            logger.warning(f"save_knowledge failed: {e}")
            return {"content": f"Could not save to memory: {e}", "metadata": {}, "images": [], "videos": [], "audios": []}

    _tool.name = "save_knowledge"
    return _tool


def count_knowledge(business_id: str, scopes: list[str] | None = None, **_):
    @tool
    def _tool() -> dict:
        """Get the total row count for knowledge entries. Use this first to know how many pages to fetch."""
        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(business_id=business_id)
            if storage._table is None:
                return {"content": "No entries yet.", "metadata": {"total_rows": 0}, "images": [], "videos": [], "audios": []}

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
                return {"content": "No entries yet.", "metadata": {"total_rows": 0}, "images": [], "videos": [], "audios": []}
            return {
                "content": f"Total knowledge entries: {len(scoped)}",
                "metadata": {"total_rows": len(scoped)},
                "images": [],
                "videos": [],
                "audios": [],
            }
        except Exception as e:
            logger.warning(f"count_knowledge failed: {e}")
            return {"content": f"Error: {e}", "metadata": {}, "images": [], "videos": [], "audios": []}

    _tool.name = "count_knowledge"
    return _tool


def fetch_knowledge(business_id: str, scopes: list[str] | None = None, **_):
    @tool
    def _tool(pages: list[Page]) -> dict:
        """Fetch knowledge entries in batches. Each page config must have 'limit' and 'offset' keys. Use count_knowledge first to determine total pages needed."""
        from concurrent.futures import ThreadPoolExecutor

        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(business_id=business_id)
            if storage._table is None:
                return {"content": "No entries yet.", "metadata": {}, "images": [], "videos": [], "audios": []}

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
                return {"content": "No entries yet.", "metadata": {}, "images": [], "videos": [], "audios": []}

            all_images: list[str] = []

            def fetch_page(page):
                limit = page.limit or  5
                offset = page.offset or 0
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
                            all_images.extend(decoded)
                    records.append(entry)
                return {"found": True, "total": len(records),  "entries": records}

            with ThreadPoolExecutor(max_workers=min(len(pages), 10)) as executor:
                all_results = list(executor.map(fetch_page, pages))
                
            return {
                "content": json.dumps(all_results, default=str),
                "metadata": {},
                "images": all_images,
                "videos": [],
                "audios": [],
            }
        except Exception as e:
            logger.warning(f"fetch_knowledge failed: {e}")
            return {"content": f"Error: {e}", "metadata": {}, "images": [], "videos": [], "audios": []}

    _tool.name = "fetch_knowledge"
    return _tool


def get_knowledge_tools(business_id: str, scopes: list[str] | None = None) -> list:
    return [
        save_knowledge(business_id=business_id, scopes=scopes),
        count_knowledge(business_id=business_id, scopes=scopes),
        fetch_knowledge(business_id=business_id, scopes=scopes),
    ]
