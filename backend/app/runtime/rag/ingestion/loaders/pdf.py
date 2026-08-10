from __future__ import annotations

import base64
import logging
import os
import tempfile
from pathlib import Path
from typing import Any
import re
import glob
import json
import shutil


import opendataloader_pdf
import pymupdf as fitz

from app.runtime.rag.models import (
    RAGDocument,
)

from ..loader import (
    DocumentLoader,
)

logger = logging.getLogger(__name__)


class PDFLoader(
    DocumentLoader,
):
    """
    Loads PDF documents using OpenDataLoader.

    Each PDF page becomes one RAGDocument.

    Chunking is performed later by the
    DocumentSplitter.
    """

    async def load(
        self,
        *,
        source: str | Path | Any,
    ) -> list[RAGDocument]:

        if not source:
            return []

        source = str(source)

        if not source.startswith(
            "data:application/pdf",
        ):
            return []

        return await self._extract_pdf_pages(
            source,
        )

    async def _extract_pdf_pages(
        self,
        content: str,
    ) -> list[RAGDocument]:

        _, b64_data = content.split(
            ",",
            1,
        )

        pdf_bytes = base64.b64decode(
            b64_data,
        )

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as tmp:

            tmp.write(
                pdf_bytes,
            )

            tmp_path = tmp.name

        try:

            doc = fitz.open(
                tmp_path,
            )

            num_pages = len(
                doc,
            )

            logger.info(
                "PDF has %s pages, splitting for OpenDataLoader.",
                num_pages,
            )

            page_dir = tempfile.mkdtemp()

            page_paths: list[str] = []

            for page_index in range(
                num_pages,
            ):

                single_doc = fitz.open()

                single_doc.insert_pdf(
                    doc,
                    from_page=page_index,
                    to_page=page_index,
                )

                page_path = os.path.join(
                    page_dir,
                    f"page_{page_index + 1}.pdf",
                )

                single_doc.save(
                    page_path,
                )

                single_doc.close()

                page_paths.append(
                    page_path,
                )

            doc.close()

            output_dir = tempfile.mkdtemp()

            opendataloader_pdf.convert(
                input_path=page_paths,
                output_dir=output_dir,
                format="markdown,json",
                quiet=True,
                image_output="external",
                image_format="jpeg",
                content_safety_off="all",
                use_struct_tree=True,
            )

            documents: list[RAGDocument] = []

            for page_index, page_path in enumerate(
                page_paths,
            ):

                page_number = (
                    page_index + 1
                )

                stem = os.path.splitext(
                    os.path.basename(
                        page_path,
                    )
                )[0]

                md_path = os.path.join(
                    output_dir,
                    stem + ".md",
                )

                json_path = os.path.join(
                    output_dir,
                    stem + ".json",
                )

                markdown = ""

                page_json: dict[str, Any] | None = None

                if os.path.exists(json_path):

                    with open(
                        json_path,
                        "r",
                        encoding="utf-8",
                    ) as file:

                        page_json = json.load(
                            file,
                        )

                page_images: list[str] = []

                image_dir = os.path.join(
                    output_dir,
                    stem,
                )

                if not os.path.isdir(
                    image_dir,
                ):
                    image_dir = output_dir

                image_files = sorted(
                    glob.glob(
                        os.path.join(
                            image_dir,
                            f"{stem}*.jpeg",
                        )
                    )
                    + glob.glob(
                        os.path.join(
                            image_dir,
                            f"{stem}*.jpg",
                        )
                    )
                    + glob.glob(
                        os.path.join(
                            image_dir,
                            f"{stem}*.png",
                        )
                    )
                )

                for image_file in image_files:

                    try:

                        with open(
                            image_file,
                            "rb",
                        ) as file:

                            image_bytes = file.read()

                        extension = (
                            os.path.splitext(
                                image_file,
                            )[1]
                            .lower()
                            .lstrip(".")
                        )

                        mime = (
                            "image/jpeg"
                            if extension in (
                                "jpg",
                                "jpeg",
                            )
                            else f"image/{extension}"
                        )

                        encoded = (
                            base64.b64encode(
                                image_bytes,
                            )
                            .decode("utf-8")
                        )

                        page_images.append(
                            f"data:{mime};base64,{encoded}"
                        )

                    except Exception as error:

                        logger.warning(
                            "Failed to read image '%s': %s",
                            image_file,
                            error,
                        )

                blocks = self._extract_page_blocks(
                    page_json,
                )

                matched_blocks = (
                    self._match_blocks_to_markdown(
                        markdown,
                        blocks,
                    )
                )

                documents.append(
                    RAGDocument(
                        id="",
                        parent_id="",
                        title=f"Page {page_number}",
                        source="pdf",
                        content=markdown,
                        metadata={
                            "page": page_number,
                            "json_blocks": matched_blocks,
                            "images": page_images,
                        },
                    )
                )

            shutil.rmtree(
                page_dir,
                ignore_errors=True,
            )

            shutil.rmtree(
                output_dir,
                ignore_errors=True,
            )

            return documents

        except ImportError:

            logger.error(
                "opendataloader-pdf is not installed.",
            )

            return []

        except Exception as error:

            logger.exception(
                "PDF extraction failed.",
                exc_info=error,
            )

            return []

        finally:

            if os.path.exists(
                tmp_path,
            ):
                os.unlink(
                    tmp_path,
                )

    def _extract_page_blocks(
        self,
        page_json: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """
        Extract normalized content blocks from the
        OpenDataLoader JSON output.
        """

        if not page_json:
            return []

        pages = page_json.get(
            "pages",
            [],
        )

        if not pages:
            return []

        page = pages[0]

        blocks: list[dict[str, Any]] = []

        for block in page.get(
            "children",
            [],
        ):

            block_type = block.get(
                "type",
                "",
            )

            text = ""

            if block_type == "paragraph":

                text = self._extract_kids_text(
                    block.get(
                        "children",
                        [],
                    )
                )

            elif block_type == "heading":

                text = self._extract_kids_text(
                    block.get(
                        "children",
                        [],
                    )
                )

            elif block_type == "list":

                text = self._extract_kids_text(
                    block.get(
                        "children",
                        [],
                    )
                )

            elif block_type == "table":

                text = self._extract_table_text(
                    block,
                )

            elif block_type == "code":

                text = self._extract_kids_text(
                    block.get(
                        "children",
                        [],
                    )
                )

            elif block_type == "quote":

                text = self._extract_kids_text(
                    block.get(
                        "children",
                        [],
                    )
                )

            else:

                text = self._extract_kids_text(
                    block.get(
                        "children",
                        [],
                    )
                )

            text = text.strip()

            if not text:
                continue

            blocks.append(
                {
                    "type": block_type,
                    "text": text,
                }
            )

        return blocks

    def _extract_kids_text(
        self,
        children: list[dict[str, Any]],
    ) -> str:
        """
        Recursively extract text from OpenDataLoader
        child nodes.
        """

        parts: list[str] = []

        for child in children:

            text = child.get(
                "text",
            )

            if text:
                parts.append(
                    str(text),
                )

            value = child.get(
                "value",
            )

            if value:
                parts.append(
                    str(value),
                )

            content = child.get(
                "content",
            )

            if isinstance(
                content,
                str,
            ):
                parts.append(
                    content,
                )

            nested = child.get(
                "children",
            )

            if nested:

                nested_text = self._extract_kids_text(
                    nested,
                )

                if nested_text:

                    parts.append(
                        nested_text,
                    )

        return " ".join(
            part.strip()
            for part in parts
            if part and part.strip()
        )

    def _extract_table_text(
        self,
        table: dict[str, Any],
    ) -> str:
        """
        Extract readable text from a table block.

        The output is a flattened textual representation
        suitable for semantic search.
        """

        rows: list[str] = []

        for row in table.get(
            "children",
            [],
        ):

            cells: list[str] = []

            for cell in row.get(
                "children",
                [],
            ):

                text = self._extract_kids_text(
                    cell.get(
                        "children",
                        [],
                    )
                ).strip()

                if text:
                    cells.append(
                        text,
                    )

            if cells:

                rows.append(
                    " | ".join(
                        cells,
                    )
                )

        if rows:
            return "\n".join(
                rows,
            )

        #
        # Fallback for unexpected table structures.
        #
        return self._extract_kids_text(
            table.get(
                "children",
                [],
            )
        )

    def _match_blocks_to_markdown(
        self,
        markdown: str,
        blocks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Match extracted JSON blocks back to the generated
        Markdown.

        Each returned block contains the original metadata
        together with the Markdown snippet that best
        represents it.
        """

        if not markdown.strip():
            return blocks

        markdown_lines = [
            line.strip()
            for line in markdown.splitlines()
            if line.strip()
        ]

        matched: list[dict[str, Any]] = []

        for block in blocks:

            text = block.get(
                "text",
                "",
            ).strip()

            if not text:

                matched.append(
                    block,
                )

                continue

            normalized = re.sub(
                r"\s+",
                " ",
                text,
            ).strip()

            markdown_match = ""

            for line in markdown_lines:

                candidate = re.sub(
                    r"\s+",
                    " ",
                    line,
                ).strip()

                if (
                    normalized in candidate
                    or candidate in normalized
                ):

                    markdown_match = line
                    break

            matched.append(
                {
                    **block,
                    "markdown": markdown_match,
                }
            )

        return matched
