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
Return the total number of records available in the master repository. 

Use this function before executing sequential or paginated browse actions 
        """
        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(business_id=business_id)
            if storage._table is None:
                return {"content": "No entries yet.", "metadata": {"total_rows": 0}, "images": [], "videos": [], "audios": []}

            df = storage._table.to_pandas()
            if scopes:
                valid_prefixes = [s.rstrip("/") for s in scopes if s and s.strip("/")]
                if valid_prefixes:
                    def _row_matches(scope_val):
                        if isinstance(scope_val, list):
                            return any(s in valid_prefixes or any(s.startswith(p) for p in valid_prefixes) for s in scope_val)
                        return False

                    mask = df["scope"].apply(_row_matches)
                    scoped = df[mask]
                else:
                    scoped = df
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


def browse_information_in_pages(business_id: str, scopes: list[str] | None = None, **_):
    @tool
    def _tool(pages: list[Page]) -> dict:
        """
Browse the master information repository sequentially in pages when targeted semantic search is insufficient.

Use this function when the request requires a broad sweep, overview, sequential audit, or complete contextual understanding of the available information corpus.
        """
        from concurrent.futures import ThreadPoolExecutor

        try:
            from app.memory.lancedb import LanceDBStorage

            storage = LanceDBStorage(business_id=business_id)
            if storage._table is None:
                return {"content": "No entries yet.", "metadata": {}, "images": [], "videos": [], "audios": []}

            df = storage._table.to_pandas()
            if scopes:
                valid_prefixes = [s.rstrip("/") for s in scopes if s and s.strip("/")]
                if valid_prefixes:
                    def _row_matches(scope_val):
                        if isinstance(scope_val, list):
                            return any(s in valid_prefixes or any(s.startswith(p) for p in valid_prefixes) for s in scope_val)
                        return False

                    mask = df["scope"].apply(_row_matches)
                    scoped = df[mask].iloc[::-1].reset_index(drop=True)
                else:
                    scoped = df.iloc[::-1].reset_index(drop=True)
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

    _tool.name = "browse_information_in_pages"
    return _tool


def search_information_with_semantic_search(business_id: str, scopes: list[str] | None = None, **_):
    @tool
    async def _tool(query:str,offset:int=0 ,limit:int=5) -> dict:
        """ 
Search the master information repository for any entity, topic, data point, keyword, or asset.

Use this function whenever the request references a specific concept, item, category, procedure, scenario, query, or any identifiable information point.

CRITICAL: All records, items, domain details, and contextual data are structurally stored inside this master repository. You MUST execute this search to see if data exists. Do not assume or guess content availability.

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

    _tool.name = "search_information_with_semantic_search"
    return _tool


def get_knowledge_tools(business_id: str, scopes: list[str] | None = None) -> list:
    return [
        save_knowledge(business_id=business_id, scopes=scopes),
        count_knowledge(business_id=business_id, scopes=scopes),
        browse_information_in_pages(business_id=business_id, scopes=scopes),
        search_information_with_semantic_search(business_id=business_id, scopes=scopes)
    ]
