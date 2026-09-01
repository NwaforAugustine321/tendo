import asyncio

from app.rag_pipeline.pipeline import Pipeline
from app.rag_pipeline.interface import DocumentSource, SourceType

import json
import base64
# from IPython.display import display, Image, Markdown


async def main():

    pipeline = Pipeline(

        namespace="test",
    )

    print("4. Ingesting text file...", flush=True)

    source = DocumentSource(
        type=SourceType.FILE,
        value="test_v1.txt",
    )

    result = await pipeline.ingest(
        collection="documents",
        source=source,
    )

    print("5. INGEST RESULT:", result, flush=True)

    print("6. Searching...", flush=True)

    result = await pipeline.search(
        query="who is tendo?",
        collections=["documents"],
        top_k=5,
    )

    print("7. SEARCH RESULT:", result, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
