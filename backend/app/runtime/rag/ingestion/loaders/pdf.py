from __future__ import annotations

import base64
import glob
import json
import logging
import os
import re
import shutil
import tempfile
from html import escape
from pathlib import Path
from typing import Any

import opendataloader_pdf
from markdownify import markdownify as html_to_markdown

from app.runtime.rag.models import RAGDocument
from ..loader import DocumentLoader


logger = logging.getLogger(__name__)


class PDFLoader(DocumentLoader):
    """
    PDF -> OpenDataLoader JSON -> HTML -> Markdown.

    JSON is the single source of truth.

    The OpenDataLoader JSON hierarchy is reconstructed into semantic HTML
    before converting HTML to Markdown.

    Supported OpenDataLoader structures:

    Root:
        - file name
        - number of pages
        - author
        - title
        - creation date
        - modification date
        - kids

    Common:
        - type
        - id
        - level
        - page number
        - bounding box

    Text:
        - font
        - font size
        - text color
        - content
        - hidden text

    Headings:
        - heading level

    Captions:
        - linked content id

    Tables:
        - number of rows
        - number of columns
        - previous table id
        - next table id
        - rows

    Table rows:
        - row number
        - cells

    Table cells:
        - row number
        - column number
        - row span
        - column span
        - kids

    Lists:
        - numbering style
        - number of list items
        - previous list id
        - next list id
        - list items

    List items:
        - kids

    Images:
        - source
        - data
        - format

    Headers / footers:
        - kids

    Text blocks:
        - kids

    Important:

    - No hybrid extraction.
    - No PDF text extraction fallback.
    - No [IMAGE] placeholder.
    - JSON is authoritative.
    - JSON is converted to HTML first.
    - HTML is converted to Markdown second.
    - Table structure is reconstructed from rows/cells.
    - List structure is reconstructed from list items.
    - Nested content is preserved.
    - Coordinates are used for ordering.
    - Original JSON layout is retained in metadata.
    """

    # ======================================================================
    # PUBLIC API
    # ======================================================================

    async def load(
        self,
        *,
        source: str | Path | Any,
        content_type: str | None = None,
    ) -> list[RAGDocument]:

        if not source:
            return []

        source = str(source)

        if not source.startswith("data:application/pdf"):
            logger.warning(
                "PDFLoader received non-PDF source."
            )
            return []

        return await self._extract_pdf(source)

    # ======================================================================
    # PDF EXTRACTION
    # ======================================================================

    async def _extract_pdf(
        self,
        content: str,
    ) -> list[RAGDocument]:

        try:
            _, b64_data = content.split(",", 1)
            pdf_bytes = base64.b64decode(b64_data)

        except Exception:
            logger.exception(
                "Invalid PDF data URI."
            )
            return []

        tmp_path: str | None = None
        output_dir: str | None = None

        try:
            # --------------------------------------------------------------
            # Write PDF
            # --------------------------------------------------------------

            with tempfile.NamedTemporaryFile(
                suffix=".pdf",
                delete=False,
            ) as tmp:

                tmp.write(pdf_bytes)
                tmp_path = tmp.name

            output_dir = tempfile.mkdtemp()

            # --------------------------------------------------------------
            # OpenDataLoader
            # --------------------------------------------------------------

            logger.info(
                "Running OpenDataLoader JSON extraction."
            )

            opendataloader_pdf.convert(
                input_path=[tmp_path],
                output_dir=output_dir,
                format="json",
                quiet=True,
                image_output="external",
                image_format="jpeg",
                content_safety_off="all",
                reading_order="xycut",
                table_method="cluster",
            )

            # --------------------------------------------------------------
            # Locate JSON
            # --------------------------------------------------------------

            json_path = self._find_json_file(
                output_dir=output_dir,
                pdf_stem=Path(tmp_path).stem,
            )

            if not json_path:
                logger.error(
                    "OpenDataLoader did not produce JSON."
                )
                return []

            logger.info(
                "OpenDataLoader JSON: %s",
                json_path,
            )

            # --------------------------------------------------------------
            # Read JSON
            # --------------------------------------------------------------

            with open(
                json_path,
                "r",
                encoding="utf-8",
            ) as file:

                document_json = json.load(file)

            # --------------------------------------------------------------
            # Build pages
            # --------------------------------------------------------------

            pages = self._build_pages(
                document_json
            )

            if not pages:
                logger.warning(
                    "OpenDataLoader returned no usable pages."
                )
                return []

            documents: list[RAGDocument] = []

            # --------------------------------------------------------------
            # Process every page
            # --------------------------------------------------------------

            for page_number in sorted(pages):

                nodes = pages[page_number]

                # ----------------------------------------------------------
                # JSON -> HTML
                # ----------------------------------------------------------

                page_html = self._page_to_html(
                    nodes
                )

                # ----------------------------------------------------------
                # HTML -> Markdown
                # ----------------------------------------------------------

                page_markdown = self._html_to_markdown(
                    page_html
                )

                # ----------------------------------------------------------
                # Normalize JSON
                # ----------------------------------------------------------

                json_blocks = []

                for node in nodes:

                    normalized = self._normalize_node(
                        node,
                        page_number,
                    )

                    if normalized:
                        json_blocks.append(
                            normalized
                        )

                # ----------------------------------------------------------
                # Images
                # ----------------------------------------------------------

                page_images = self._extract_page_images(
                    output_dir=output_dir,
                    nodes=nodes,
                )

                logger.info(
                    "PDF page %s extracted: nodes=%s images=%s chars=%s",
                    page_number,
                    len(nodes),
                    len(page_images),
                    len(page_markdown),
                )

                documents.append(
                    RAGDocument(
                        id="",
                        parent_id="",
                        title=f"Page {page_number}",
                        source="pdf",
                        content=page_markdown,
                        metadata={
                            "source_type": "pdf",
                            "page": page_number,
                            "json_blocks": json_blocks,
                            "images": page_images,
                            "html": page_html,
                            "markdown_length": len(
                                page_markdown
                            ),
                            "block_count": len(
                                json_blocks
                            ),
                            "content_source": (
                                "json_to_html_to_markdown"
                            ),
                        },
                    )
                )

            return documents

        except ImportError:
            logger.error(
                "Required PDF dependencies are not installed."
            )
            return []

        except Exception:
            logger.exception(
                "PDF extraction failed."
            )
            return []

        finally:

            if output_dir:
                shutil.rmtree(
                    output_dir,
                    ignore_errors=True,
                )

            if tmp_path and os.path.exists(
                tmp_path
            ):

                try:
                    os.unlink(tmp_path)

                except OSError:
                    pass

    # ======================================================================
    # FIND JSON
    # ======================================================================

    def _find_json_file(
        self,
        *,
        output_dir: str,
        pdf_stem: str,
    ) -> str | None:

        direct = os.path.join(
            output_dir,
            f"{pdf_stem}.json",
        )

        if os.path.isfile(direct):
            return direct

        candidates = sorted(
            glob.glob(
                os.path.join(
                    output_dir,
                    "**",
                    "*.json",
                ),
                recursive=True,
            )
        )

        return (
            candidates[0]
            if candidates
            else None
        )

    # ======================================================================
    # BUILD PAGES
    # ======================================================================

    def _build_pages(
        self,
        document_json: Any,
    ) -> dict[int, list[dict[str, Any]]]:

        pages: dict[
            int,
            list[dict[str, Any]],
        ] = {}

        if not isinstance(
            document_json,
            dict,
        ):
            return pages

        # --------------------------------------------------------------
        # OpenDataLoader root:
        #
        # {
        #     "kids": [...]
        # }
        #
        # IMPORTANT:
        #
        # We add only ROOT nodes to the page.
        #
        # Children stay inside their parent so tables/lists retain
        # their hierarchy.
        # --------------------------------------------------------------

        kids = document_json.get("kids")

        if isinstance(
            kids,
            list,
        ):

            for node in kids:

                if not isinstance(
                    node,
                    dict,
                ):
                    continue

                page_number = self._get_page_number(
                    node,
                    1,
                )

                pages.setdefault(
                    page_number,
                    [],
                ).append(node)

            return self._sort_pages(
                pages
            )

        # --------------------------------------------------------------
        # Explicit pages
        # --------------------------------------------------------------

        explicit_pages = document_json.get(
            "pages"
        )

        if isinstance(
            explicit_pages,
            list,
        ):

            for index, page in enumerate(
                explicit_pages,
                start=1,
            ):

                if not isinstance(
                    page,
                    dict,
                ):
                    continue

                page_number = self._get_page_number(
                    page,
                    index,
                )

                children = self._get_structural_children(
                    page
                )

                if children:

                    pages.setdefault(
                        page_number,
                        [],
                    ).extend(
                        children
                    )

                elif self._looks_like_content_node(
                    page
                ):

                    pages.setdefault(
                        page_number,
                        [],
                    ).append(page)

            return self._sort_pages(
                pages
            )

        # --------------------------------------------------------------
        # Generic recursive document
        # --------------------------------------------------------------

        self._walk_root(
            document_json,
            pages,
            current_page=1,
        )

        return self._sort_pages(
            pages
        )

    # ======================================================================
    # GENERIC ROOT WALK
    # ======================================================================

    def _walk_root(
        self,
        value: Any,
        pages: dict[int, list[dict[str, Any]]],
        current_page: int,
    ) -> None:

        if isinstance(
            value,
            list,
        ):

            for item in value:

                self._walk_root(
                    item,
                    pages,
                    current_page,
                )

            return

        if not isinstance(
            value,
            dict,
        ):
            return

        page_number = self._get_page_number(
            value,
            current_page,
        )

        if self._looks_like_content_node(
            value
        ):

            pages.setdefault(
                page_number,
                [],
            ).append(value)

            # ----------------------------------------------------------
            # Once a content node is found, do NOT recursively register
            # its children as separate page blocks.
            #
            # The children belong to this structural node.
            # ----------------------------------------------------------

            return

        # Otherwise continue looking for content nodes.

        for key, child in value.items():

            if key in {
                "metadata",
                "meta",
            }:
                continue

            self._walk_root(
                child,
                pages,
                page_number,
            )

    # ======================================================================
    # PAGE SORT
    # ======================================================================

    def _sort_pages(
        self,
        pages: dict[
            int,
            list[dict[str, Any]],
        ],
    ) -> dict[
        int,
        list[dict[str, Any]],
    ]:

        result = {}

        for page in sorted(pages):

            nodes = self._deduplicate_nodes(
                pages[page]
            )

            result[page] = self._sort_nodes(
                nodes
            )

        return result

    # ======================================================================
    # DEDUPLICATION
    # ======================================================================

    def _deduplicate_nodes(
        self,
        nodes: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:

        result = []

        seen_ids: set[str] = set()
        seen_objects: set[int] = set()

        for node in nodes:

            if not isinstance(
                node,
                dict,
            ):
                continue

            node_id = node.get(
                "id"
            )

            if node_id is not None:

                key = str(
                    node_id
                )

                if key in seen_ids:
                    continue

                seen_ids.add(
                    key
                )

            else:

                object_id = id(
                    node
                )

                if object_id in seen_objects:
                    continue

                seen_objects.add(
                    object_id
                )

            result.append(
                node
            )

        return result

    # ======================================================================
    # STRUCTURAL CHILDREN
    # ======================================================================

    def _get_structural_children(
        self,
        node: dict[str, Any],
    ) -> list[dict[str, Any]]:

        children: list[
            dict[str, Any]
        ] = []

        # Generic children.
        for key in (
            "children",
            "kids",
            "elements",
            "items",
            "blocks",
        ):

            value = node.get(
                key
            )

            if isinstance(
                value,
                list,
            ):

                children.extend(
                    item
                    for item in value
                    if isinstance(
                        item,
                        dict,
                    )
                )

        # --------------------------------------------------------------
        # TABLE:
        #
        # rows is structural, not children.
        # --------------------------------------------------------------

        rows = node.get(
            "rows"
        )

        if isinstance(
            rows,
            list,
        ):

            children.extend(
                row
                for row in rows
                if isinstance(
                    row,
                    dict,
                )
            )

        # --------------------------------------------------------------
        # LIST:
        #
        # list items is structural, not children.
        # --------------------------------------------------------------

        list_items = node.get(
            "list items"
        )

        if isinstance(
            list_items,
            list,
        ):

            children.extend(
                item
                for item in list_items
                if isinstance(
                    item,
                    dict,
                )
            )

        return children

    # ======================================================================
    # ALL CHILDREN
    # ======================================================================

    def _get_children(
        self,
        node: dict[str, Any],
    ) -> list[dict[str, Any]]:

        children = self._get_structural_children(
            node
        )

        # --------------------------------------------------------------
        # Deduplicate while retaining order.
        # --------------------------------------------------------------

        result = []

        seen: set[int] = set()

        for child in children:

            object_id = id(
                child
            )

            if object_id in seen:
                continue

            seen.add(
                object_id
            )

            result.append(
                child
            )

        return result

    # ======================================================================
    # PAGE NUMBER
    # ======================================================================

    def _get_page_number(
        self,
        node: dict[str, Any],
        fallback: int,
    ) -> int:

        for key in (
            "page number",
            "page_number",
            "page",
            "pageIndex",
            "page_index",
        ):

            value = node.get(
                key
            )

            try:

                if value is not None:

                    number = int(
                        value
                    )

                    if number > 0:
                        return number

            except (
                TypeError,
                ValueError,
            ):
                pass

        return fallback

    # ======================================================================
    # VISUAL SORT
    # ======================================================================

    def _sort_nodes(
        self,
        nodes: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:

        positioned = []
        unpositioned = []

        for index, node in enumerate(
            nodes
        ):

            bbox = self._get_bbox(
                node
            )

            if not bbox:

                unpositioned.append(
                    (
                        index,
                        node,
                    )
                )

                continue

            x1, y1, x2, y2 = bbox

            positioned.append(
                (
                    -y2,
                    x1,
                    index,
                    node,
                )
            )

        positioned.sort()

        result = [
            item[3]
            for item in positioned
        ]

        result.extend(
            node
            for _, node in sorted(
                unpositioned
            )
        )

        return result

    # ======================================================================
    # JSON -> HTML
    # ======================================================================

    def _page_to_html(
        self,
        nodes: list[
            dict[str, Any]
        ],
    ) -> str:

        parts = []

        for node in nodes:

            html = self._node_to_html(
                node
            )

            if html.strip():
                parts.append(
                    html
                )

        return "\n".join(
            parts
        )

    # ======================================================================
    # NODE -> HTML
    # ======================================================================

    def _node_to_html(
        self,
        node: Any,
    ) -> str:

        if node is None:
            return ""

        if isinstance(
            node,
            str,
        ):
            return escape(
                node
            )

        if isinstance(
            node,
            (int, float),
        ):
            return escape(
                str(node)
            )

        if isinstance(
            node,
            list,
        ):

            return "\n".join(
                self._node_to_html(
                    item
                )
                for item in node
                if isinstance(
                    item,
                    (dict, str, int, float),
                )
            )

        if not isinstance(
            node,
            dict,
        ):
            return ""

        node_type = self._node_type(
            node
        )

        # ==============================================================
        # TABLE
        # ==============================================================

        if node_type in {
            "table",
            "tbl",
            "data_table",
            "grid",
        }:

            return self._table_to_html(
                node
            )

        # ==============================================================
        # TABLE ROW
        # ==============================================================

        if node_type in {
            "table row",
            "table_row",
            "row",
            "tr",
        }:

            return self._table_row_to_html(
                node
            )

        # ==============================================================
        # TABLE CELL
        # ==============================================================

        if node_type in {
            "table cell",
            "table_cell",
            "cell",
            "td",
            "th",
        }:

            return self._table_cell_to_html(
                node
            )

        # ==============================================================
        # HEADING
        # ==============================================================

        if node_type in {
            "heading",
            "title",
            "document_title",
            "doc_title",
            "doctitle",
            "subtitle",
            "section_title",
            "section_heading",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:

            level = self._heading_level(
                node
            )

            return (
                f"<h{level}>"
                + self._inline_html(
                    node
                )
                + f"</h{level}>"
            )

        # ==============================================================
        # PARAGRAPH / TEXT
        # ==============================================================

        if node_type in {
            "paragraph",
            "p",
            "text",
            "text_block",
            "textline",
            "text_line",
            "line",
            "body",
            "body_text",
        }:

            return (
                "<p>"
                + self._inline_html(
                    node
                )
                + "</p>"
            )

        # ==============================================================
        # SPAN / INLINE
        # ==============================================================

        if node_type in {
            "span",
            "inline_text",
            "text_run",
            "run",
        }:

            return self._inline_html(
                node
            )

        # ==============================================================
        # LIST
        # ==============================================================

        if node_type in {
            "list",
            "ul",
            "unordered_list",
            "unordered",
            "bullet_list",
        }:

            return self._list_to_html(
                node,
                ordered=False,
            )

        if node_type in {
            "ol",
            "ordered_list",
            "ordered",
            "numbered_list",
        }:

            return self._list_to_html(
                node,
                ordered=True,
            )

        # ==============================================================
        # LIST ITEM
        # ==============================================================

        if node_type in {
            "list item",
            "list_item",
            "li",
            "item",
        }:

            return self._list_item_to_html(
                node
            )

        # ==============================================================
        # QUOTE
        # ==============================================================

        if node_type in {
            "quote",
            "blockquote",
            "quotation",
            "pullquote",
        }:

            return (
                "<blockquote>"
                + self._inline_html(
                    node
                )
                + "</blockquote>"
            )

        # ==============================================================
        # CODE
        # ==============================================================

        if node_type in {
            "code",
            "code_block",
            "source_code",
        }:

            text = self._extract_direct_text(
                node
            )

            return (
                "<pre><code>"
                + escape(text)
                + "</code></pre>"
            )

        if node_type in {
            "pre",
            "preformatted",
        }:

            text = self._extract_direct_text(
                node
            )

            return (
                "<pre>"
                + escape(text)
                + "</pre>"
            )

        # ==============================================================
        # LINK
        # ==============================================================

        if node_type in {
            "link",
            "hyperlink",
            "a",
            "url",
        }:

            href = (
                node.get("href")
                or node.get("url")
                or node.get("target")
                or node.get("destination")
            )

            text = self._inline_html(
                node
            )

            if href:

                return (
                    '<a href="'
                    + escape(
                        str(href),
                        quote=True,
                    )
                    + '">'
                    + text
                    + "</a>"
                )

            return text

        # ==============================================================
        # IMAGE
        # ==============================================================

        if node_type in {
            "image",
            "img",
            "figure",
            "drawing",
            "graphic",
            "picture",
            "illustration",
            "chart",
            "diagram",
            "vector",
        }:

            return self._image_to_html(
                node
            )

        # ==============================================================
        # CAPTION
        # ==============================================================

        if node_type in {
            "caption",
            "figcaption",
            "figure_caption",
        }:

            return (
                "<figcaption>"
                + self._inline_html(
                    node
                )
                + "</figcaption>"
            )

        # ==============================================================
        # FOOTNOTE
        # ==============================================================

        if node_type in {
            "footnote",
            "foot_note",
            "endnote",
            "note",
        }:

            return (
                "<p>"
                + self._inline_html(
                    node
                )
                + "</p>"
            )

        # ==============================================================
        # HEADER / FOOTER
        # ==============================================================

        if node_type == "header":

            return (
                "<header>"
                + self._children_to_html(
                    node
                )
                + "</header>"
            )

        if node_type == "footer":

            return (
                "<footer>"
                + self._children_to_html(
                    node
                )
                + "</footer>"
            )

        # ==============================================================
        # TEXT BLOCK
        # ==============================================================

        if node_type in {
            "text block",
            "text_block_container",
        }:

            return (
                "<div>"
                + self._children_to_html(
                    node
                )
                + "</div>"
            )

        # ==============================================================
        # HR
        # ==============================================================

        if node_type in {
            "hr",
            "separator",
            "horizontal_rule",
            "divider",
        }:

            return "<hr>"

        # ==============================================================
        # GENERIC HTML TAG
        # ==============================================================

        tag = self._safe_html_tag(
            node
        )

        if tag:

            children = self._get_children(
                node
            )

            if children:

                return (
                    f"<{tag}>"
                    + "".join(
                        self._node_to_html(
                            child
                        )
                        for child in self._sort_nodes(
                            children
                        )
                    )
                    + f"</{tag}>"
                )

            text = self._extract_direct_text(
                node
            )

            if tag == "br":
                return "<br>"

            return (
                f"<{tag}>"
                + escape(text)
                + f"</{tag}>"
            )

        # ==============================================================
        # UNKNOWN CONTAINER
        #
        # Never discard unknown JSON structures.
        # ==============================================================

        children = self._get_children(
            node
        )

        if children:

            return self._children_to_html(
                node
            )

        text = self._extract_node_text(
            node
        )

        if text:

            return (
                "<p>"
                + escape(text)
                + "</p>"
            )

        return ""

    # ======================================================================
    # CHILDREN -> HTML
    # ======================================================================

    def _children_to_html(
        self,
        node: dict[str, Any],
    ) -> str:

        children = self._sort_nodes(
            self._get_children(
                node
            )
        )

        return "".join(
            self._node_to_html(
                child
            )
            for child in children
        )

    # ======================================================================
    # INLINE HTML
    # ======================================================================

    def _inline_html(
        self,
        node: dict[str, Any],
    ) -> str:

        children = self._get_children(
            node
        )

        # --------------------------------------------------------------
        # If this is a text node whose children are actual inline runs,
        # preserve the runs.
        # --------------------------------------------------------------

        if children:

            return "".join(
                self._node_to_html(
                    child
                )
                for child in self._sort_nodes(
                    children
                )
            )

        text = self._extract_direct_text(
            node
        )

        if not text:
            return ""

        result = escape(
            text
        )

        font = str(
            node.get("font")
            or ""
        ).lower()

        # --------------------------------------------------------------
        # Font-based formatting
        # --------------------------------------------------------------

        if any(
            value in font
            for value in (
                "bold",
                "semibold",
                "demibold",
                "black",
            )
        ):

            result = (
                "<strong>"
                + result
                + "</strong>"
            )

        if any(
            value in font
            for value in (
                "italic",
                "oblique",
            )
        ):

            result = (
                "<em>"
                + result
                + "</em>"
            )

        # --------------------------------------------------------------
        # Explicit formatting fields
        # --------------------------------------------------------------

        if node.get(
            "bold"
        ) is True:

            result = (
                "<strong>"
                + result
                + "</strong>"
            )

        if node.get(
            "italic"
        ) is True:

            result = (
                "<em>"
                + result
                + "</em>"
            )

        if node.get(
            "underline"
        ) is True:

            result = (
                "<u>"
                + result
                + "</u>"
            )

        return result

    # ======================================================================
    # TABLE -> HTML
    # ======================================================================

    def _table_to_html(
        self,
        table: dict[str, Any],
    ) -> str:

        rows = self._get_table_rows(
            table
        )

        if not rows:

            text = self._extract_node_text(
                table
            )

            return (
                "<p>"
                + escape(text)
                + "</p>"
                if text
                else ""
            )

        html = [
            "<table>"
        ]

        # --------------------------------------------------------------
        # Table caption if present.
        # --------------------------------------------------------------

        caption = self._find_table_caption(
            table
        )

        if caption:

            html.append(
                "<caption>"
                + escape(caption)
                + "</caption>"
            )

        # --------------------------------------------------------------
        # Rows
        # --------------------------------------------------------------

        for row in rows:

            html.append(
                self._table_row_to_html(
                    row
                )
            )

        html.append(
            "</table>"
        )

        return "\n".join(
            html
        )

    # ======================================================================
    # TABLE ROWS
    # ======================================================================

    def _get_table_rows(
        self,
        table: dict[str, Any],
    ) -> list[
        dict[str, Any]
    ]:

        rows: list[
            dict[str, Any]
        ] = []

        # --------------------------------------------------------------
        # THIS IS THE IMPORTANT FIX.
        #
        # OpenDataLoader uses:
        #
        # table["rows"]
        #
        # rather than:
        #
        # table["children"]
        # --------------------------------------------------------------

        explicit_rows = table.get(
            "rows"
        )

        if isinstance(
            explicit_rows,
            list,
        ):

            rows.extend(
                row
                for row in explicit_rows
                if isinstance(
                    row,
                    dict,
                )
            )

        # Some versions may expose rows through kids/children.
        if not rows:

            for child in self._get_children(
                table
            ):

                child_type = self._node_type(
                    child
                )

                if child_type in {
                    "table row",
                    "table_row",
                    "row",
                    "tr",
                }:

                    rows.append(
                        child
                    )

        # --------------------------------------------------------------
        # Preserve row_number order.
        # --------------------------------------------------------------

        def row_key(
            row: dict[str, Any]
        ):

            value = (
                row.get("row number")
                or row.get("row_number")
                or row.get("row")
            )

            try:
                return (
                    0,
                    int(value),
                )
            except (
                TypeError,
                ValueError,
            ):
                return (
                    1,
                    0,
                )

        rows.sort(
            key=row_key
        )

        return rows

    # ======================================================================
    # TABLE ROW -> HTML
    # ======================================================================

    def _table_row_to_html(
        self,
        row: dict[str, Any],
    ) -> str:

        cells = self._get_table_cells(
            row
        )

        if not cells:
            return "<tr></tr>"

        parts = [
            "<tr>"
        ]

        for cell in cells:

            parts.append(
                self._table_cell_to_html(
                    cell
                )
            )

        parts.append(
            "</tr>"
        )

        return "".join(
            parts
        )

    # ======================================================================
    # TABLE CELLS
    # ======================================================================

    def _get_table_cells(
        self,
        row: dict[str, Any],
    ) -> list[
        dict[str, Any]
    ]:

        cells: list[
            dict[str, Any]
        ] = []

        # --------------------------------------------------------------
        # OpenDataLoader schema:
        #
        # row["cells"]
        # --------------------------------------------------------------

        explicit_cells = row.get(
            "cells"
        )

        if isinstance(
            explicit_cells,
            list,
        ):

            cells.extend(
                cell
                for cell in explicit_cells
                if isinstance(
                    cell,
                    dict,
                )
            )

        # --------------------------------------------------------------
        # Also support generic child structure.
        # --------------------------------------------------------------

        if not cells:

            for child in self._get_children(
                row
            ):

                if self._node_type(
                    child
                ) in {
                    "table cell",
                    "table_cell",
                    "cell",
                    "td",
                    "th",
                }:

                    cells.append(
                        child
                    )

        # --------------------------------------------------------------
        # Column order is explicit in the JSON.
        # --------------------------------------------------------------

        def column_key(
            cell: dict[str, Any]
        ):

            value = (
                cell.get("column number")
                or cell.get("column_number")
                or cell.get("column")
            )

            try:
                return (
                    0,
                    int(value),
                )
            except (
                TypeError,
                ValueError,
            ):
                return (
                    1,
                    0,
                )

        cells.sort(
            key=column_key
        )

        return cells

    # ======================================================================
    # TABLE CELL -> HTML
    # ======================================================================

    def _table_cell_to_html(
        self,
        cell: dict[str, Any],
    ) -> str:

        cell_type = self._node_type(
            cell
        )

        tag = (
            "th"
            if cell_type == "th"
            else "td"
        )

        attributes = []

        # --------------------------------------------------------------
        # rowspan
        # --------------------------------------------------------------

        row_span = (
            cell.get("row span")
            or cell.get("row_span")
            or 1
        )

        try:

            row_span = int(
                row_span
            )

            if row_span > 1:

                attributes.append(
                    f' rowspan="{row_span}"'
                )

        except (
            TypeError,
            ValueError,
        ):
            pass

        # --------------------------------------------------------------
        # colspan
        # --------------------------------------------------------------

        column_span = (
            cell.get("column span")
            or cell.get("column_span")
            or 1
        )

        try:

            column_span = int(
                column_span
            )

            if column_span > 1:

                attributes.append(
                    f' colspan="{column_span}"'
                )

        except (
            TypeError,
            ValueError,
        ):
            pass

        # --------------------------------------------------------------
        # Cell content comes from:
        #
        # cell["kids"]
        #
        # This is another important part of the OpenDataLoader schema.
        # --------------------------------------------------------------

        children = self._get_children(
            cell
        )

        if children:

            content = "".join(
                self._node_to_html(
                    child
                )
                for child in self._sort_nodes(
                    children
                )
            )

        else:

            content = escape(
                self._extract_direct_text(
                    cell
                )
            )

        return (
            f"<{tag}"
            + "".join(
                attributes
            )
            + ">"
            + content
            + f"</{tag}>"
        )

    # ======================================================================
    # TABLE CAPTION
    # ======================================================================

    def _find_table_caption(
        self,
        table: dict[str, Any],
    ) -> str:

        caption = table.get(
            "caption"
        )

        if isinstance(
            caption,
            str,
        ):

            return caption.strip()

        for child in self._get_children(
            table
        ):

            if self._node_type(
                child
            ) in {
                "caption",
                "figcaption",
                "figure_caption",
            }:

                return self._extract_node_text(
                    child
                )

        return ""

    # ======================================================================
    # LIST -> HTML
    # ======================================================================

    def _list_to_html(
        self,
        node: dict[str, Any],
        *,
        ordered: bool,
    ) -> str:

        # --------------------------------------------------------------
        # Respect OpenDataLoader numbering style.
        # --------------------------------------------------------------

        numbering_style = str(
            node.get("numbering style")
            or ""
        ).lower()

        if numbering_style:

            ordered = any(
                token in numbering_style
                for token in (
                    "ordered",
                    "number",
                    "decimal",
                    "alpha",
                    "roman",
                )
            )

        tag = (
            "ol"
            if ordered
            else "ul"
        )

        # --------------------------------------------------------------
        # OpenDataLoader:
        #
        # list["list items"]
        # --------------------------------------------------------------

        items = node.get(
            "list items"
        )

        if not isinstance(
            items,
            list,
        ):

            items = [
                child
                for child in self._get_children(
                    node
                )
                if self._node_type(
                    child
                ) in {
                    "list item",
                    "list_item",
                    "li",
                    "item",
                }
            ]

        parts = [
            f"<{tag}>"
        ]

        for item in items:

            if not isinstance(
                item,
                dict,
            ):
                continue

            parts.append(
                self._list_item_to_html(
                    item
                )
            )

        parts.append(
            f"</{tag}>"
        )

        return "".join(
            parts
        )

    # ======================================================================
    # LIST ITEM -> HTML
    # ======================================================================

    def _list_item_to_html(
        self,
        item: dict[str, Any],
    ) -> str:

        children = self._get_children(
            item
        )

        if children:

            content = "".join(
                self._node_to_html(
                    child
                )
                for child in self._sort_nodes(
                    children
                )
            )

        else:

            content = escape(
                self._extract_direct_text(
                    item
                )
            )

        return (
            "<li>"
            + content
            + "</li>"
        )

    # ======================================================================
    # IMAGE -> HTML
    # ======================================================================

    def _image_to_html(
        self,
        node: dict[str, Any],
    ) -> str:

        # --------------------------------------------------------------
        # IMPORTANT:
        #
        # Never emit [IMAGE].
        #
        # We preserve textual metadata.
        # --------------------------------------------------------------

        text = self._extract_image_text(
            node
        )

        children = self._get_children(
            node
        )

        if text:

            return (
                "<figure>"
                "<figcaption>"
                + escape(text)
                + "</figcaption>"
                "</figure>"
            )

        if children:

            return (
                "<figure>"
                + "".join(
                    self._node_to_html(
                        child
                    )
                    for child in children
                )
                + "</figure>"
            )

        return ""

    # ======================================================================
    # HTML -> MARKDOWN
    # ======================================================================

    def _html_to_markdown(
        self,
        page_html: str,
    ) -> str:

        if not page_html.strip():
            return ""

        # --------------------------------------------------------------
        # Do NOT use strip_document="STRIP".
        #
        # That caused:
        #
        # ValueError: Invalid value for strip_document: STRIP
        # --------------------------------------------------------------

        markdown = html_to_markdown(
            page_html,
            heading_style="ATX",
            bullets="*",
            strong_em_symbol="*",
            newline_style="backslash",
        )

        return self._clean_markdown(
            markdown
        )

    # ======================================================================
    # CLEAN MARKDOWN
    # ======================================================================

    def _clean_markdown(
        self,
        markdown: str,
    ) -> str:

        markdown = (
            markdown
            .replace(
                "\r\n",
                "\n",
            )
            .replace(
                "\r",
                "\n",
            )
        )

        # --------------------------------------------------------------
        # Never keep image placeholders.
        # --------------------------------------------------------------

        markdown = re.sub(
            r"(?im)"
            r"^[ \t]*\[IMAGE\][ \t]*$",
            "",
            markdown,
        )

        # --------------------------------------------------------------
        # Remove generated Markdown image syntax.
        #
        # Image content itself is intentionally not part of textual RAG
        # content. Captions/alt descriptions remain.
        # --------------------------------------------------------------

        markdown = re.sub(
            r"!\[[^\]]*\]"
            r"\(\s*(?:<[^>]+>|[^)\s]+)"
            r"(?:\s+[^)]*)?\)",
            "",
            markdown,
        )

        markdown = re.sub(
            r"!\[[^\]]*\]\[[^\]]*\]",
            "",
            markdown,
        )

        # --------------------------------------------------------------
        # Preserve tables.
        #
        # Only collapse excessive blank lines.
        # --------------------------------------------------------------

        markdown = re.sub(
            r"\n{3,}",
            "\n\n",
            markdown,
        )

        return markdown.strip()

    # ======================================================================
    # NODE TYPE
    # ======================================================================

    def _node_type(
        self,
        node: dict[str, Any],
    ) -> str:

        value = (
            node.get("type")
            or node.get("tag")
            or node.get("element")
            or node.get("kind")
            or ""
        )

        return str(
            value
        ).strip().lower()

    # ======================================================================
    # SAFE HTML TAG
    # ======================================================================

    def _safe_html_tag(
        self,
        node: dict[str, Any],
    ) -> str | None:

        value = (
            node.get("html_tag")
            or node.get("tag")
            or node.get("element")
        )

        if not value:
            return None

        tag = str(
            value
        ).strip().lower()

        allowed = {
            "article",
            "section",
            "header",
            "footer",
            "main",
            "aside",
            "nav",
            "div",
            "span",
            "p",
            "strong",
            "b",
            "em",
            "i",
            "u",
            "small",
            "mark",
            "del",
            "ins",
            "sub",
            "sup",
            "br",
            "pre",
            "code",
            "blockquote",
            "ul",
            "ol",
            "li",
            "table",
            "thead",
            "tbody",
            "tfoot",
            "tr",
            "td",
            "th",
            "caption",
            "figure",
            "figcaption",
            "a",
            "hr",
        }

        return (
            tag
            if tag in allowed
            else None
        )

    # ======================================================================
    # HEADING LEVEL
    # ======================================================================

    def _heading_level(
        self,
        node: dict[str, Any],
    ) -> int:

        for key in (
            "heading level",
            "heading_level",
        ):

            value = node.get(
                key
            )

            try:

                if value is not None:

                    return max(
                        1,
                        min(
                            6,
                            int(value),
                        ),
                    )

            except (
                TypeError,
                ValueError,
            ):
                pass

        node_type = self._node_type(
            node
        )

        match = re.fullmatch(
            r"h([1-6])",
            node_type,
        )

        if match:
            return int(
                match.group(1)
            )

        level = str(
            node.get("level")
            or ""
        ).lower()

        if "document" in level:
            return 1

        if "title" in level:
            return 1

        if "subtitle" in level:
            return 2

        if "section" in level:
            return 2

        return 2

    # ======================================================================
    # DIRECT TEXT
    # ======================================================================

    def _extract_direct_text(
        self,
        node: dict[str, Any],
    ) -> str:

        parts = []

        # --------------------------------------------------------------
        # OpenDataLoader text uses "content".
        # --------------------------------------------------------------

        for key in (
            "content",
            "text",
            "value",
            "label",
            "title",
            "caption",
            "alt",
            "alt_text",
            "description",
            "string",
        ):

            value = node.get(
                key
            )

            if isinstance(
                value,
                str,
            ) and value.strip():

                parts.append(
                    value.strip()
                )

        return " ".join(
            parts
        ).strip()

    # ======================================================================
    # FULL TEXT
    # ======================================================================

    def _extract_node_text(
        self,
        node: Any,
    ) -> str:

        if node is None:
            return ""

        if isinstance(
            node,
            str,
        ):
            return node.strip()

        if isinstance(
            node,
            (int, float),
        ):
            return str(node)

        if isinstance(
            node,
            list,
        ):

            return " ".join(
                text
                for item in node
                if (
                    text :=
                    self._extract_node_text(
                        item
                    )
                )
            ).strip()

        if not isinstance(
            node,
            dict,
        ):
            return ""

        parts = []

        direct = self._extract_direct_text(
            node
        )

        if direct:
            parts.append(
                direct
            )

        # --------------------------------------------------------------
        # Text runs.
        # --------------------------------------------------------------

        for key in (
            "text_runs",
            "spans",
            "runs",
        ):

            value = node.get(
                key
            )

            if isinstance(
                value,
                list,
            ):

                for item in value:

                    text = self._extract_node_text(
                        item
                    )

                    if text:
                        parts.append(
                            text
                        )

        # --------------------------------------------------------------
        # Structural children.
        # --------------------------------------------------------------

        for child in self._get_children(
            node
        ):

            text = self._extract_node_text(
                child
            )

            if text:
                parts.append(
                    text
                )

        return " ".join(
            parts
        ).strip()

    # ======================================================================
    # IMAGE TEXT
    # ======================================================================

    def _extract_image_text(
        self,
        node: dict[str, Any],
    ) -> str:

        for key in (
            "alt",
            "alt_text",
            "caption",
            "description",
            "title",
            "text",
            "content",
        ):

            value = node.get(
                key
            )

            if (
                isinstance(
                    value,
                    str,
                )
                and value.strip()
            ):

                return value.strip()

        return ""

    # ======================================================================
    # BOUNDING BOX
    # ======================================================================

    def _get_bbox(
        self,
        node: dict[str, Any],
    ) -> tuple[
        float,
        float,
        float,
        float,
    ] | None:

        for key in (
            "bounding box",
            "bounding_box",
            "bbox",
            "box",
            "coordinates",
        ):

            value = node.get(
                key
            )

            if not isinstance(
                value,
                (list, tuple),
            ):
                continue

            if len(value) != 4:
                continue

            try:

                x1, y1, x2, y2 = map(
                    float,
                    value,
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

            if (
                x2 <= x1
                or y2 <= y1
            ):
                continue

            return (
                x1,
                y1,
                x2,
                y2,
            )

        return None

    # ======================================================================
    # CONTENT NODE DETECTION
    # ======================================================================

    def _looks_like_content_node(
        self,
        node: Any,
    ) -> bool:

        if not isinstance(
            node,
            dict,
        ):
            return False

        node_type = self._node_type(
            node
        )

        if node_type:
            return True

        return bool(
            self._get_bbox(
                node
            )
            or any(
                key in node
                for key in (
                    "content",
                    "text",
                    "value",
                    "kids",
                    "rows",
                    "list items",
                    "cells",
                    "children",
                    "bounding box",
                    "bbox",
                )
            )
        )

    # ======================================================================
    # NORMALIZED JSON
    # ======================================================================

    def _normalize_node(
        self,
        node: dict[str, Any],
        page_number: int,
    ) -> dict[str, Any] | None:

        if not isinstance(
            node,
            dict,
        ):
            return None

        result: dict[
            str,
            Any,
        ] = {
            "type": (
                self._node_type(
                    node
                )
                or "unknown"
            ),
            "page": page_number,
        }

        # --------------------------------------------------------------
        # Preserve OpenDataLoader fields.
        # --------------------------------------------------------------

        for key in (
            "id",
            "page",
            "page_number",
            "page number",
            "bounding box",
            "bounding_box",
            "bbox",
            "coordinates",
            "confidence",
            "level",
            "heading level",
            "heading_level",
            "font",
            "font size",
            "font_size",
            "text color",
            "text_color",
            "content",
            "hidden text",
            "hidden_text",
            "number of rows",
            "number of columns",
            "previous table id",
            "next table id",
            "row number",
            "column number",
            "row span",
            "column span",
            "numbering style",
            "number of list items",
            "previous list id",
            "next list id",
            "linked content id",
            "source",
            "data",
            "format",
            "href",
            "url",
            "target",
            "width",
            "height",
        ):

            if key in node:
                result[key] = node[
                    key
                ]

        text = self._extract_node_text(
            node
        )

        if text:
            result["text"] = text

        # --------------------------------------------------------------
        # Normalize structural children exactly according to schema.
        # --------------------------------------------------------------

        children = self._get_children(
            node
        )

        if children:

            normalized_children = []

            for child in children:

                normalized = self._normalize_node(
                    child,
                    page_number,
                )

                if normalized:
                    normalized_children.append(
                        normalized
                    )

            if normalized_children:

                result[
                    "children"
                ] = normalized_children

        # --------------------------------------------------------------
        # Explicit table rows.
        # --------------------------------------------------------------

        if self._node_type(
            node
        ) in {
            "table",
            "tbl",
            "data_table",
            "grid",
        }:

            rows = self._get_table_rows(
                node
            )

            result[
                "rows"
            ] = [
                self._normalize_node(
                    row,
                    page_number,
                )
                for row in rows
            ]

        return result

    # ======================================================================
    # IMAGES
    # ======================================================================

    def _extract_page_images(
        self,
        *,
        output_dir: str,
        nodes: list[
            dict[str, Any]
        ],
    ) -> list[str]:

        image_types = {
            "image",
            "img",
            "figure",
            "drawing",
            "graphic",
            "picture",
            "illustration",
            "chart",
            "diagram",
            "vector",
        }

        image_nodes = []

        def walk(
            node: dict[str, Any]
        ):

            if self._node_type(
                node
            ) in image_types:

                image_nodes.append(
                    node
                )

            for child in self._get_children(
                node
            ):

                walk(
                    child
                )

        for node in nodes:

            walk(
                node
            )

        if not image_nodes:
            return []

        image_files = sorted(
            set(
                glob.glob(
                    os.path.join(
                        output_dir,
                        "**",
                        "*.jpeg",
                    ),
                    recursive=True,
                )
                + glob.glob(
                    os.path.join(
                        output_dir,
                        "**",
                        "*.jpg",
                    ),
                    recursive=True,
                )
                + glob.glob(
                    os.path.join(
                        output_dir,
                        "**",
                        "*.png",
                    ),
                    recursive=True,
                )
            )
        )

        images = []

        for image_file in image_files:

            try:

                image_bytes = Path(
                    image_file
                ).read_bytes()

                suffix = (
                    Path(
                        image_file
                    )
                    .suffix
                    .lower()
                )

                mime = (
                    "image/jpeg"
                    if suffix in {
                        ".jpg",
                        ".jpeg",
                    }
                    else (
                        "image/"
                        + suffix.lstrip(".")
                    )
                )

                images.append(
                    "data:"
                    + mime
                    + ";base64,"
                    + base64.b64encode(
                        image_bytes
                    ).decode(
                        "utf-8"
                    )
                )

            except Exception as error:

                logger.warning(
                    "Failed to read image '%s': %s",
                    image_file,
                    error,
                )

        return images
