from __future__ import annotations


import html
import logging
from pathlib import Path
from typing import Any


import httpx
from markdownify import markdownify as html_to_markdown


from app.config.settings import settings
from app.runtime.rag.models import RAGDocument


from ..loader import DocumentLoader


logger = logging.getLogger(__name__)


class ImageLoader(DocumentLoader):
    """
    Image OCR loader using NVIDIA Nemotron OCR V2.


    Nemotron returns OCR text together with normalized bounding boxes.


    The OCR result is reconstructed into HTML using the EXACT
    bounding-box coordinates returned by Nemotron.


    No table detection is performed.
    No column detection is performed.
    No line grouping is performed.
    No paragraph inference is performed.


    The spatial relationship is preserved by positioning every OCR
    detection according to its original x/y coordinates.
    """

    OCR_URL = (
        "https://ai.api.nvidia.com/"
        "v1/cv/nvidia/nemotron-ocr-v2"
    )

    async def load(
        self,
        *,
        source: str | Path | Any,
        content_type: str | None = None,
    ) -> list[RAGDocument]:

        if not source:
            return []

        source = str(source)

        if not source.startswith("data:"):
            return []

        try:
            text = await self._image_ocr(source)

        except Exception as error:
            logger.warning(
                "OCR extraction failed: %s",
                error,
            )
            return []

        if not text.strip():
            return []

        print('text>>', text)
        return [
            RAGDocument(
                id="",
                title="",
                source="image",
                content=text,
                metadata={
                    "source_type": "image",
                    "ocr_engine": "nvidia-nemotron-ocr-v2",
                    "layout_reconstruction": (
                        "exact_bounding_box_coordinates"
                    ),
                },
            )
        ]

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------

    async def _image_ocr(
        self,
        image_data_url: str,
    ) -> str:
        """
        Run Nemotron OCR V2.


        The response is converted:


            OCR JSON
                ↓
            exact bounding boxes
                ↓
            HTML
                ↓
            Markdown


        The OCR detections themselves are never converted directly
        into Markdown.
        """

        headers = {
            "Authorization": (
                f"Bearer {settings.nvidia_api_key}"
            ),
            "Accept": "application/json",
        }

        payload = {
            "input": [
                {
                    "type": "image_url",
                    "url": image_data_url,
                }
            ]
        }

        async with httpx.AsyncClient(
            timeout=60,
        ) as client:

            response = await client.post(
                self.OCR_URL,
                headers=headers,
                json=payload,
            )

            response.raise_for_status()

            data = response.json()

        if not isinstance(data, dict):
            return ""

        pages = data.get("data", [])

        if not isinstance(pages, list):
            return ""

        html_pages: list[str] = []

        for page in pages:

            if not isinstance(page, dict):
                continue

            detections = page.get(
                "text_detections",
                [],
            )

            if not isinstance(detections, list):
                continue

            elements = self._parse_detections(
                detections,
            )

            if not elements:
                continue

            page_html = self._detections_to_html(
                elements,
            )

            if page_html:
                html_pages.append(
                    page_html,
                )

        if not html_pages:
            return ""

        html_document = "\n".join(
            html_pages,
        )

        return self._html_to_markdown(
            html_document,
        )

    # ------------------------------------------------------------------
    # Parse OCR detections
    # ------------------------------------------------------------------

    def _parse_detections(
        self,
        detections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Parse Nemotron OCR detections while preserving their original
        normalized bounding-box coordinates.


        Coordinates are NOT rounded and are NOT converted to pixels.


        Nemotron gives:


            x ∈ [0, 1]
            y ∈ [0, 1]


        We preserve those values directly.
        """

        elements: list[dict[str, Any]] = []

        for index, detection in enumerate(
            detections,
        ):

            if not isinstance(
                detection,
                dict,
            ):
                continue

            prediction = detection.get(
                "text_prediction",
                {},
            )

            if not isinstance(
                prediction,
                dict,
            ):
                continue

            text = str(
                prediction.get(
                    "text",
                    "",
                )
                or ""
            )

            if not text.strip():
                continue

            confidence_raw = prediction.get(
                "confidence",
                0.0,
            )

            try:
                confidence = float(
                    confidence_raw or 0.0
                )
            except (
                TypeError,
                ValueError,
            ):
                confidence = 0.0

            bounding_box = detection.get(
                "bounding_box",
                {},
            )

            if not isinstance(
                bounding_box,
                dict,
            ):
                continue

            points = bounding_box.get(
                "points",
                [],
            )

            if not isinstance(
                points,
                list,
            ):
                continue

            coordinates: list[
                tuple[float, float]
            ] = []

            for point in points:

                if not isinstance(
                    point,
                    dict,
                ):
                    continue

                try:
                    x = float(
                        point["x"]
                    )

                    y = float(
                        point["y"]
                    )

                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    continue

                coordinates.append(
                    (
                        x,
                        y,
                    )
                )

            if not coordinates:
                continue

            x_values = [
                coordinate[0]
                for coordinate in coordinates
            ]

            y_values = [
                coordinate[1]
                for coordinate in coordinates
            ]

            x1 = min(x_values)
            y1 = min(y_values)

            x2 = max(x_values)
            y2 = max(y_values)

            width = max(
                x2 - x1,
                0.0,
            )

            height = max(
                y2 - y1,
                0.0,
            )

            elements.append(
                {
                    "index": index,
                    "text": text,
                    "confidence": confidence,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "width": width,
                    "height": height,
                }
            )

        return elements

    # ------------------------------------------------------------------
    # Exact coordinate -> HTML
    # ------------------------------------------------------------------

    def _detections_to_html(
        self,
        elements: list[dict[str, Any]],
    ) -> str:
        """
        Convert OCR detections directly into coordinate-positioned HTML.


        THIS IS THE IMPORTANT PART.


        We intentionally do NOT:


            - group by Y
            - group by X
            - detect columns
            - detect tables
            - merge lines
            - infer paragraphs
            - infer headings
            - insert spaces based on gaps


        Every OCR detection gets its own <span> with the exact
        normalized bounding-box coordinates.


        Example:


            OCR A:
                x1=0.02
                y1=0.20
                x2=0.40
                y2=0.23


            OCR B:
                x1=0.80
                y1=0.20
                x2=0.90
                y2=0.23


        They remain physically separated in the HTML instead of being
        converted into:


            OCR A OCR B


        as one artificial paragraph.
        """

        if not elements:
            return ""

        # Preserve the natural page order only as a deterministic
        # fallback for DOM ordering.

        ordered = sorted(
            elements,
            key=lambda element: (
                element["y1"],
                element["x1"],
                element["index"],
            ),
        )

        html_elements: list[str] = []

        for element in ordered:

            text = element["text"]

            escaped_text = html.escape(
                text,
                quote=False,
            )

            # Exact normalized coordinates.

            left = self._percentage(
                element["x1"],
            )

            top = self._percentage(
                element["y1"],
            )

            width = self._percentage(
                element["width"],
            )

            height = self._percentage(
                element["height"],
            )

            html_elements.append(
                (
                    '<span '
                    'class="ocr-text" '
                    f'data-x1="{element["x1"]}" '
                    f'data-y1="{element["y1"]}" '
                    f'data-x2="{element["x2"]}" '
                    f'data-y2="{element["y2"]}" '
                    f'style="'
                    "position:absolute;"
                    f"left:{left};"
                    f"top:{top};"
                    f"width:{width};"
                    f"height:{height};"
                    '">'
                    f"{escaped_text}"
                    "</span>"
                )
            )

        # The container represents one OCR page.

        return (
            '<div class="ocr-page" '
            'style="'
            "position:relative;"
            "width:100%;"
            "height:100%;"
            '">\n'
            + "\n".join(
                html_elements,
            )
            + "\n</div>"
        )

    # ------------------------------------------------------------------
    # Coordinate formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _percentage(
        value: float,
    ) -> str:
        """
        Convert normalized coordinate to percentage.


        IMPORTANT:


        The underlying coordinate is not changed.


        Example:


            0.33013445138931274


        becomes:


            33.013445138931274%


        No rounding is applied.
        """

        return (
            f"{value * 100}%"
        )

    # ------------------------------------------------------------------
    # HTML -> Markdown
    # ------------------------------------------------------------------

    def _html_to_markdown(
        self,
        html_document: str,
    ) -> str:
        """
        Convert reconstructed OCR HTML to Markdown.


        markdownify is intentionally the LAST stage.


        OCR JSON
            ↓
        coordinate HTML
            ↓
        markdownify
            ↓
        Markdown
        """

        if not html_document.strip():
            return ""

        markdown = html_to_markdown(
            html_document,
            heading_style="ATX",
            bullets="-",
            strip=[
                "script",
                "style",
            ],
        )

        return self._clean_markdown(
            markdown,
        )

    # ------------------------------------------------------------------
    # Markdown cleanup
    # ------------------------------------------------------------------

    def _clean_markdown(
        self,
        markdown: str,
    ) -> str:
        """
        Minimal cleanup.


        Do NOT aggressively normalize whitespace because doing so can
        destroy spatially reconstructed content.
        """

        lines = [
            line.rstrip()
            for line in markdown.splitlines()
        ]

        cleaned: list[str] = []

        previous_blank = False

        for line in lines:

            if not line.strip():

                if not previous_blank:
                    cleaned.append("")

                previous_blank = True

                continue

            cleaned.append(
                line,
            )

            previous_blank = False

        return "\n".join(
            cleaned,
        ).strip()
