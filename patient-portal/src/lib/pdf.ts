import { jsPDF } from "jspdf";

const PAGE_WIDTH = 612; // US Letter, points
const PAGE_HEIGHT = 792;
const MARGIN = 56;
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN * 2;
const LINE_HEIGHT = 14;
const TITLE_FONT_SIZE = 14;
const BODY_FONT_SIZE = 9.5;

/**
 * jsPDF's built-in standard fonts (helvetica, courier, times) only support
 * the WinAnsi/Latin-1 character set. Characters outside that set — common
 * in LLM-generated text, e.g. em/en dashes, curly quotes, ellipses — have
 * no glyph in those fonts and get silently rendered as a garbled "&"
 * instead, even though the underlying text layer keeps the correct
 * character. Normalize to plain ASCII equivalents before rendering so the
 * PDF actually displays what the text says.
 */
function sanitizeForPdf(text: string): string {
  return text
    .replace(/[\u2013\u2014]/g, "-") // en dash, em dash
    .replace(/[\u2018\u2019\u201A\u02BC]/g, "'") // curly single quotes
    .replace(/[\u201C\u201D\u201E]/g, '"') // curly double quotes
    .replace(/\u2026/g, "...") // ellipsis
    .replace(/[\u2022\u25CF\u25AA]/g, "-") // bullets
    .replace(/[\u00A0\u2000-\u200A\u202F\u205F]/g, " ") // non-breaking/odd spaces
    .replace(/[\u2010-\u2012]/g, "-"); // hyphen variants
}

/**
 * Renders plain, pre-formatted text (monospace-friendly — safe for
 * already-aligned tables/columns like the insurance document) into a
 * downloadable multi-page PDF and triggers the browser download.
 */
export function downloadTextAsPdf(title: string, bodyText: string, filename: string) {
  const doc = new jsPDF({ unit: "pt", format: "letter" });
  let cursorY = MARGIN;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(TITLE_FONT_SIZE);
  const titleLines = doc.splitTextToSize(sanitizeForPdf(title), CONTENT_WIDTH);
  doc.text(titleLines, MARGIN, cursorY);
  cursorY += titleLines.length * (TITLE_FONT_SIZE + 4) + 10;

  doc.setFont("courier", "normal");
  doc.setFontSize(BODY_FONT_SIZE);

  const rawLines = sanitizeForPdf(bodyText).split("\n");
  for (const rawLine of rawLines) {
    // Wrap any line that's too wide for the page, preserving blank lines.
    const wrapped = rawLine.length === 0 ? [""] : doc.splitTextToSize(rawLine, CONTENT_WIDTH);
    for (const line of wrapped) {
      if (cursorY > PAGE_HEIGHT - MARGIN) {
        doc.addPage();
        cursorY = MARGIN;
      }
      doc.text(line, MARGIN, cursorY);
      cursorY += LINE_HEIGHT;
    }
  }

  doc.save(filename);
}

/**
 * Renders a simple labelled-section document (title + ordered list of
 * {heading, body} sections) into a downloadable PDF — used for the patient
 * consultation report, which is structured data rather than one
 * pre-formatted block of text.
 */
export function downloadSectionsAsPdf(
  title: string,
  sections: Array<{ heading?: string; body: string }>,
  filename: string,
) {
  const doc = new jsPDF({ unit: "pt", format: "letter" });
  let cursorY = MARGIN;

  const ensureSpace = (needed: number) => {
    if (cursorY + needed > PAGE_HEIGHT - MARGIN) {
      doc.addPage();
      cursorY = MARGIN;
    }
  };

  doc.setFont("helvetica", "bold");
  doc.setFontSize(TITLE_FONT_SIZE + 2);
  const titleLines = doc.splitTextToSize(sanitizeForPdf(title), CONTENT_WIDTH);
  doc.text(titleLines, MARGIN, cursorY);
  cursorY += titleLines.length * (TITLE_FONT_SIZE + 6) + 12;

  for (const section of sections) {
    if (section.heading) {
      ensureSpace(LINE_HEIGHT + 8);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(BODY_FONT_SIZE + 1);
      doc.text(sanitizeForPdf(section.heading), MARGIN, cursorY);
      cursorY += LINE_HEIGHT + 2;
    }

    doc.setFont("helvetica", "normal");
    doc.setFontSize(BODY_FONT_SIZE + 1);
    const bodyLines = doc.splitTextToSize(sanitizeForPdf(section.body || "-"), CONTENT_WIDTH);
    for (const line of bodyLines) {
      ensureSpace(LINE_HEIGHT);
      doc.text(line, MARGIN, cursorY);
      cursorY += LINE_HEIGHT;
    }
    cursorY += 10;
  }

  doc.save(filename);
}
