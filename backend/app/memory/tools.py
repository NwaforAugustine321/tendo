import json
import logging
from langchain_core.tools import tool
from app.memory.memory import Memory
from pydantic import BaseModel, model_validator
from typing import TypedDict, Any

class Page(BaseModel):
    limit: int
    offset: int
    query: str

    @model_validator(mode="before")
    @classmethod
    def strip_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {k.strip(): v for k, v in data.items()}
        return data

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
        """
Return the total number of business knowledge records. Use this before browsing the knowledge base to determine how many pages are available. This tool is generally not required for semantic searches.
        """
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


def browse_business_knowledge(business_id: str, scopes: list[str] | None = None, **_):
    @tool
    def _tool(pages: list[Page]) -> dict:
        """
Browse the business knowledge base sequentially.

Use this tool when the user requests a broad understanding of the business or the knowledge corpus as a whole.

Do **not** use this tool when the request is about a specific entity or identifiable business concept. Use **search_business_knowledge** instead.

Browse only the amount of information needed to answer the request, evaluating after each retrieval whether additional pages are necessary.
        """
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
            logger.warning(f"browse_business_knowledge failed: {e}")
            return {"content": f"Error: {e}", "metadata": {}, "images": [], "videos": [], "audios": []}

    _tool.name = "browse_business_knowledge"
    return _tool


def search_business_knowledge(business_id: str, scopes: list[str] | None = None, **_):
    @tool
    async def _tool(query:str,offset:int=0 ,limit:int=5) -> dict:
        """ 
Search the business knowledge base using semantic and keyword retrieval.

Use this tool when the request references a specific entity, topic, keyword, customer, supplier, product, project, document, identifier, policy, procedure, recipe, scenario, story, or other identifiable business concept.

Do **not** use this tool for broad overview requests. Use **browse_business_knowledge** instead.

Construct precise search queries using the most specific identifiers available, and perform additional searches only when a clearly identified knowledge gap remains.

        """

        try:
            search_scopes = scopes or [f"/business/{business_id}"]
            memory = Memory(scopes=search_scopes, business_id=business_id)
            results = await memory.recall(query=query, limit=limit)

            if not results:
                return {"content": "No relevant results found.", "metadata": {}, "images": [], "videos": [], "audios": []}

            all_images: list[str] = []
            entries = []
            for record in results:
                entries.append({"content": record.content})
                if record.images:
                    all_images.extend(record.images)
        
            return {
                "content": json.dumps(entries, default=str),
                "metadata": {"total": len(entries)},
                "images": all_images,
                "videos": [],
                "audios": [],
            }
        except Exception as e:
            logger.warning(f"search_business_knowledge failed: {e}")
            return {"content": f"Error: {e}", "metadata": {}, "images": [], "videos": [], "audios": []}

    _tool.name = "search_business_knowledge"
    return _tool


def get_knowledge_tools(business_id: str, scopes: list[str] | None = None) -> list:
    return [
        save_knowledge(business_id=business_id, scopes=scopes),
        count_knowledge(business_id=business_id, scopes=scopes),
        browse_business_knowledge(business_id=business_id, scopes=scopes),
        search_business_knowledge(business_id=business_id, scopes=scopes)
    ]
