import React, {
  type CSSProperties,
  type MouseEvent,
  type ReactNode,
} from "react";

/* -------------------------------------------------------------------------- */
/* Types                                                                      */
/* -------------------------------------------------------------------------- */

export interface PdfElementData {
  type: string;

  id: number | string;

  level?: string;

  "page number": number;

  "bounding box": [number, number, number, number];

  "heading level"?: number;

  font?: string;

  "font size"?: number;

  "text color"?: string;

  content?: string | null;

  /*
   * Optional fields that may be produced by different
   * OpenDataLoader versions/configurations.
   */
  src?: string;

  image?: string;

  url?: string;

  href?: string;

  alt?: string;

  align?: string;

  "text alignment"?: string;

  "line height"?: number;

  "font weight"?: number | string;

  "font style"?: string;

  opacity?: number;

  rotation?: number;

  zIndex?: number;

  children?: PdfElementData[];

  [key: string]: unknown;
}

export interface PdfData {
  "file name": string;

  "number of pages": number;

  author?: string | null;

  title?: string | null;

  "creation date"?: string | null;

  "modification date"?: string | null;

  /*
   * Optional page metadata if your backend provides it.
   */
  pages?: PdfPageData[];

  kids: PdfElementData[];
}

export interface PdfPageData {
  page: number;

  width?: number;

  height?: number;

  rotation?: number;
}

export interface PdfLayoutProps {
  data: PdfData;

  pageWidth?: number;

  pageHeight?: number;

  scale?: number;

  onElementClick?: (element: PdfElementData) => void;
}

/* -------------------------------------------------------------------------- */
/* PDF Element                                                                */
/* -------------------------------------------------------------------------- */

interface PdfElementProps {
  element: PdfElementData;

  pageHeight: number;

  scale: number;

  onClick?: (element: PdfElementData) => void;
}

export function PdfElement({
  element,
  pageHeight,
  scale,
  onClick,
}: PdfElementProps): React.ReactElement | null {
  const bbox = element["bounding box"];

  if (!Array.isArray(bbox) || bbox.length !== 4) {
    return null;
  }

  const [x1, y1, x2, y2] = bbox;

  if (
    !Number.isFinite(x1) ||
    !Number.isFinite(y1) ||
    !Number.isFinite(x2) ||
    !Number.isFinite(y2)
  ) {
    return null;
  }

  const width = x2 - x1;
  const height = y2 - y1;

  if (width <= 0 || height <= 0) {
    return null;
  }

  /*
   * PDF:
   *
   *      origin = bottom-left
   *
   * Browser:
   *
   *      origin = top-left
   */

  const left = x1;

  const top = pageHeight - y2;

  const style: CSSProperties = {
    position: "absolute",

    left: left * scale,

    top: top * scale,

    width: width * scale,

    height: height * scale,

    boxSizing: "border-box",

    margin: 0,

    padding: 0,

    fontFamily: getFontFamily(element.font),

    fontSize: element["font size"] ? element["font size"] * scale : undefined,

    color: parsePdfColor(element["text color"]),

    fontWeight: getFontWeight(element),

    fontStyle: getFontStyle(element),

    lineHeight: element["line height"]
      ? element["line height"] * scale
      : undefined,

    textAlign: getTextAlignment(element),

    whiteSpace: "normal",

    overflowWrap: "break-word",

    /*
     * Important:
     *
     * Do not clip normal text.
     */
    overflow: isImageElement(element) ? "hidden" : "visible",

    opacity: typeof element.opacity === "number" ? element.opacity : undefined,

    transform: element.rotation ? `rotate(${element.rotation}deg)` : undefined,

    zIndex: typeof element.zIndex === "number" ? element.zIndex : undefined,
  };

  const handleClick = (event: MouseEvent<HTMLDivElement>) => {
    event.stopPropagation();

    onClick?.(element);
  };

  const className = [
    "pdf-layout-element",

    `pdf-layout-${normalizeType(element.type)}`,
  ].join(" ");

  /* ---------------------------------------------------------------------- */
  /* Image                                                                  */
  /* ---------------------------------------------------------------------- */

  if (isImageElement(element)) {
    return (
      <div
        className={className}
        style={style}
        data-id={element.id}
        data-page={element["page number"]}
        onClick={handleClick}
      >
        {renderImage(element)}
      </div>
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Text / HTML / semantic content                                        */
  /* ---------------------------------------------------------------------- */

  return (
    <div
      className={className}
      style={style}
      data-id={element.id}
      data-page={element["page number"]}
      data-type={element.type}
      onClick={handleClick}
    >
      {renderContent(element)}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Content Renderer                                                           */
/* -------------------------------------------------------------------------- */

function renderContent(element: PdfElementData): ReactNode {
  /*
   * If children exist, render them.
   */
  if (Array.isArray(element.children) && element.children.length > 0) {
    return element.children.map((child) => (
      <PdfElement key={child.id} element={child} pageHeight={0} scale={1} />
    ));
  }

  const content = element.content;

  if (content === undefined || content === null) {
    return null;
  }

  /*
   * If the source explicitly marks the
   * content as HTML, you can enable
   * this behavior here.
   *
   * IMPORTANT:
   * Only use dangerouslySetInnerHTML
   * if the HTML has been sanitized.
   */

  if (looksLikeHtml(content)) {
    return (
      <span
        dangerouslySetInnerHTML={{
          __html: sanitizeHtml(content),
        }}
      />
    );
  }

  return content;
}

/* -------------------------------------------------------------------------- */
/* Image Renderer                                                             */
/* -------------------------------------------------------------------------- */

function renderImage(element: PdfElementData): ReactNode {
  const src = element.src ?? element.image ?? element.content;

  if (!src) {
    return <div className="pdf-layout-image-placeholder">Image</div>;
  }

  return (
    <img
      src={src}
      alt={element.alt ?? ""}
      draggable={false}
      style={{
        width: "100%",
        height: "100%",
        objectFit: "contain",
        display: "block",
      }}
    />
  );
}

/* -------------------------------------------------------------------------- */
/* Element Classification                                                     */
/* -------------------------------------------------------------------------- */

function normalizeType(type: string): string {
  return String(type)
    .toLowerCase()
    .trim()
    .replace(/[\s_-]+/g, "-");
}

function isImageElement(element: PdfElementData): boolean {
  const type = normalizeType(element.type);

  return type === "image" || type === "figure" || type === "picture";
}

/* -------------------------------------------------------------------------- */
/* Text Alignment                                                             */
/* -------------------------------------------------------------------------- */

function getTextAlignment(element: PdfElementData): CSSProperties["textAlign"] {
  const alignment = element["text alignment"] ?? element.align;

  if (typeof alignment === "string") {
    const value = alignment.toLowerCase();

    if (value.includes("center")) {
      return "center";
    }

    if (value.includes("right")) {
      return "right";
    }

    if (value.includes("justify")) {
      return "justify";
    }
  }

  /*
   * Paragraphs are justified by default.
   */
  if (normalizeType(element.type) === "paragraph") {
    return "justify";
  }

  return "left";
}

/* -------------------------------------------------------------------------- */
/* Font                                                                       */
/* -------------------------------------------------------------------------- */

function getFontFamily(font?: string): string {
  if (!font) {
    return "Times New Roman, Times, serif";
  }

  const value = font.toLowerCase();

  if (value.includes("nimbusrom") || value.includes("times")) {
    return '"Times New Roman", Times, serif';
  }

  if (value.includes("nimbusmon") || value.includes("courier")) {
    return '"Courier New", Courier, monospace';
  }

  if (value.includes("helvetica") || value.includes("arial")) {
    return "Arial, Helvetica, sans-serif";
  }

  return `"${font}", serif`;
}

function getFontWeight(element: PdfElementData): CSSProperties["fontWeight"] {
  if (
    typeof element["font weight"] === "number" ||
    typeof element["font weight"] === "string"
  ) {
    return element["font weight"] as CSSProperties["fontWeight"];
  }

  return isBold(element.font) ? 600 : undefined;
}

function getFontStyle(element: PdfElementData): CSSProperties["fontStyle"] {
  if (element["font style"]) {
    return element["font style"] as CSSProperties["fontStyle"];
  }

  return isItalic(element.font) ? "italic" : undefined;
}

function isBold(font?: string): boolean {
  if (!font) {
    return false;
  }

  const value = font.toLowerCase();

  return (
    value.includes("bold") ||
    value.includes("medi") ||
    value.includes("black") ||
    value.includes("heavy")
  );
}

function isItalic(font?: string): boolean {
  if (!font) {
    return false;
  }

  const value = font.toLowerCase();

  return value.includes("ital") || value.includes("obli");
}

/* -------------------------------------------------------------------------- */
/* PDF Color                                                                  */
/* -------------------------------------------------------------------------- */

function parsePdfColor(value?: string): string | undefined {
  if (!value) {
    return undefined;
  }

  const numbers = String(value)
    .replace(/[\[\]]/g, "")
    .split(",")
    .map(Number)
    .filter(Number.isFinite);

  if (!numbers.length) {
    return undefined;
  }

  if (numbers.length === 1) {
    const gray = Math.round(Math.max(0, Math.min(1, numbers[0])) * 255);

    return `rgb(${gray}, ${gray}, ${gray})`;
  }

  const [r, g, b] = numbers;

  return `rgb(
    ${Math.round(r * 255)},
    ${Math.round(g * 255)},
    ${Math.round(b * 255)}
  )`;
}

/* -------------------------------------------------------------------------- */
/* HTML Detection                                                             */
/* -------------------------------------------------------------------------- */

function looksLikeHtml(value: string): boolean {
  return /<([a-z][\w-]*)(?:\s[^>]*)?>/i.test(value);
}

/*
 * IMPORTANT:
 *
 * This is intentionally conservative.
 *
 * For production, use a real HTML sanitizer
 * such as DOMPurify before rendering arbitrary
 * HTML from a document parser.
 */
function sanitizeHtml(value: string): string {
  if (typeof window === "undefined") {
    return value;
  }

  const template = document.createElement("template");

  template.innerHTML = value;

  const dangerous = template.content.querySelectorAll(
    "script, iframe, object, embed, style, link",
  );

  dangerous.forEach((node) => node.remove());

  return template.innerHTML;
}

/* -------------------------------------------------------------------------- */
/* Page Grouping                                                              */
/* -------------------------------------------------------------------------- */

export function groupByPage(
  elements: PdfElementData[],
): Map<number, PdfElementData[]> {
  const pages = new Map<number, PdfElementData[]>();

  for (const element of elements) {
    const page = Number(element["page number"]) || 1;

    if (!pages.has(page)) {
      pages.set(page, []);
    }

    pages.get(page)!.push(element);
  }

  return pages;
}

/* -------------------------------------------------------------------------- */
/* Element Ordering                                                           */
/* -------------------------------------------------------------------------- */

export function compareElements(a: PdfElementData, b: PdfElementData): number {
  const za = typeof a.zIndex === "number" ? a.zIndex : 0;

  const zb = typeof b.zIndex === "number" ? b.zIndex : 0;

  if (za !== zb) {
    return za - zb;
  }

  return Number(a.id) - Number(b.id);
}

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

export const pdfLayoutStyles = `
  .pdf-layout-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;

    width: 100%;
    height: 100%;

    overflow: auto;

    padding: 20px;

    background: #e5e7eb;

    box-sizing: border-box;
  }

  .pdf-layout-page {
    position: relative;

    flex: 0 0 auto;

    background: white;

    overflow: hidden;

    box-shadow:
      0 1px 3px rgba(0, 0, 0, 0.12),
      0 8px 24px rgba(0, 0, 0, 0.08);
  }

  .pdf-layout-element {
    position: absolute;

    box-sizing: border-box;

    margin: 0;
    padding: 0;

    overflow-wrap: break-word;

    white-space: normal;

    line-height: normal;
  }

  .pdf-layout-paragraph {
    text-align: justify;

    text-justify: inter-word;

    hyphens: auto;
  }

  .pdf-layout-heading {
    text-align: left;
  }

  .pdf-layout-caption {
    text-align: center;

    font-style: italic;
  }

  .pdf-layout-footnote {
    font-size: 0.85em;
  }

  .pdf-layout-code {
    font-family:
      "Courier New",
      Courier,
      monospace;

    white-space: pre-wrap;
  }

  .pdf-layout-quote {
    font-style: italic;
  }

  .pdf-layout-image,
  .pdf-layout-figure,
  .pdf-layout-picture {
    overflow: hidden;
  }

  .pdf-layout-image-placeholder {
    width: 100%;
    height: 100%;

    display: flex;

    align-items: center;

    justify-content: center;

    background: #f3f4f6;

    color: #9ca3af;

    font-size: 12px;
  }

  .pdf-layout-element:hover {
    outline:
      1px solid
      rgba(59, 130, 246, 0.4);

    cursor: pointer;
  }
`;
