"""Build a PDF from the editable academic CV data."""

import argparse
from html import escape
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from fonts import ensure_fonts


ROOT = Path(__file__).resolve().parent
INK = "#17263A"
TEXT = "#26374A"
MUTED = "#43566A"
GREEN = "#146652"
RULE = "#C6D8DA"
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 38
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

STYLES = {
    "name": ParagraphStyle("name", fontName="CVBold", fontSize=38, leading=40, textColor=INK),
    "intro": ParagraphStyle("intro", fontName="CV", fontSize=11, leading=14, textColor=TEXT, spaceAfter=7),
    "section": ParagraphStyle("section", fontName="CVBold", fontSize=15, leading=17.5, textColor=GREEN),
    "entry": ParagraphStyle("entry", fontName="CVBold", fontSize=11, leading=12.8, textColor=INK),
    "date": ParagraphStyle("date", alignment=TA_RIGHT, fontName="CV", fontSize=9.3, leading=12, textColor=MUTED),
    "detail": ParagraphStyle("detail", fontName="CV", fontSize=10.2, leading=11.8, textColor=TEXT),
    "paper_title": ParagraphStyle("paper_title", fontName="CVBold", fontSize=10.8, leading=12.9, textColor=INK),
    "paper_metadata": ParagraphStyle("paper_metadata", fontName="CV", fontSize=9.8, leading=12.2, textColor=MUTED),
    "award": ParagraphStyle("award", fontName="CV", fontSize=9.65, leading=12.2, textColor=TEXT),
}


class Divider(Flowable):
    def __init__(self):
        super().__init__()
        self.width = CONTENT_WIDTH
        self.height = 1

    def draw(self):
        self.canv.setStrokeColor(colors.HexColor(RULE))
        self.canv.setLineWidth(0.65)
        self.canv.line(0, 0, self.width, 0)


def paragraph(markup, style):
    return Paragraph(markup, STYLES[style])


def linked_label(label, url=None):
    if url:
        return f'<link href="{escape(url)}" color="{GREEN}">{escape(label)}</link>'
    return escape(label)


def heading(label, before, after):
    return KeepTogether([
        Spacer(1, before),
        paragraph(escape(label), "section"),
        Spacer(1, 4),
        Divider(),
        Spacer(1, after),
    ])


def dated_entry(item, space):
    title = paragraph(linked_label(item["title"], item.get("url")), "entry")
    date = paragraph(escape(item["date"]), "date")
    pair = Table([[title, date]], colWidths=[CONTENT_WIDTH - 134, 134])
    pair.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    detail = "<br/>".join(escape(line) for line in item["details"])
    return KeepTogether([pair, paragraph(detail, "detail"), Spacer(1, space)])


def publication(item, display_name):
    title = linked_label(item["title"], item.get("url"))
    authors = []
    for author in item.get("authors", []):
        author_markup = escape(author)
        if author.rstrip("†").strip() == display_name:
            author_markup = f"<b>{escape(display_name)}</b>{escape(author[len(display_name):])}"
        authors.append(author_markup)
    metadata = escape(item["status"])
    if authors:
        metadata = f"{', '.join(authors)} · {metadata}"
    return KeepTogether([
        paragraph(title, "paper_title"),
        paragraph(metadata, "paper_metadata"),
        Spacer(1, 6.7),
    ])


def award(item):
    event = linked_label(item["title"], item.get("url"))
    result, role, date = (escape(item[key]) for key in ("result", "role", "date"))
    date = date.replace(" · ", " <b>·</b> ")
    return KeepTogether([
        paragraph(f"<b>{result}</b> · {event}<br/>{role} · {date}", "award"),
        Spacer(1, 3.7),
    ])


def build_story(data):
    profile = data["profile"]
    name_markup = escape(profile["name"])
    if alternate_name := profile.get("alternate_name"):
        name_markup += f' <font name="CVChinese" size="20" color="{GREEN}">{escape(alternate_name)}</font>'
    affiliation = escape(profile["affiliation"])
    if website := profile.get("website"):
        affiliation += " · " + linked_label(website["label"], website["url"])
    story = [
        paragraph(name_markup, "name"),
        Spacer(1, 4),
        paragraph(affiliation, "intro"),
        paragraph(f'<b>Research interests</b> · {escape(profile["research_interests"])}', "intro"),
    ]
    for section in data["sections"]:
        starts_page = section.get("new_page", False)
        if starts_page:
            story.append(PageBreak())
        kind = section["kind"]
        before = 4 if starts_page else 5
        after = 4
        if kind == "awards":
            before, after = 8, 5
        story.append(heading(section["title"], before, after))
        if kind == "entries":
            space = section.get("entry_spacing", 2)
            story.extend(dated_entry(item, space) for item in section["items"])
        elif kind == "publications":
            story.extend(publication(item, profile["name"]) for item in section["items"])
        elif kind == "awards":
            story.extend(award(item) for item in section["items"])
        else:
            raise ValueError(f"Unknown section kind: {kind}")
        if note := section.get("note"):
            story.append(paragraph(escape(note), "paper_metadata"))
    if footer := data.get("closing_note"):
        story.append(Spacer(1, 6))
        story.append(paragraph(f'<b>{escape(footer["label"])}</b> · {escape(footer["text"])}', "detail"))
    return story


def build_pdf(data, output, expected_pages):
    fonts = ensure_fonts(ROOT / "build" / "fonts")
    for name, filename in (
        ("CV", "Carlito-Regular.ttf"),
        ("CVBold", "Carlito-Bold.ttf"),
        ("CVChinese", "NotoSansSC-Regular.ttf"),
    ):
        pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    pdfmetrics.registerFontFamily("CV", normal="CV", bold="CVBold")

    name = data["profile"]["name"]

    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(GREEN))
        canvas.rect(MARGIN, PAGE_HEIGHT - 40, 28, 2.1, fill=1, stroke=0)
        if doc.page > 1:
            canvas.setFont("CVBold", 10)
            canvas.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 41, name)
        canvas.setStrokeColor(colors.HexColor(RULE))
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN, 34, PAGE_WIDTH - MARGIN, 34)
        canvas.setFont("CV", 9)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(MARGIN, 21, f"{name} · Academic CV")
        canvas.drawRightString(PAGE_WIDTH - MARGIN, 21, str(doc.page))
        canvas.restoreState()

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        staged_pdf = Path(temporary) / "cv.pdf"
        doc = SimpleDocTemplate(
            str(staged_pdf),
            pagesize=A4,
            leftMargin=MARGIN - 6,
            rightMargin=MARGIN - 6,
            topMargin=46,
            bottomMargin=40,
            title=f"{name} | Academic CV",
            author=name,
            subject="Academic curriculum vitae",
            invariant=1,
        )
        doc.build(build_story(data), onFirstPage=draw_page, onLaterPages=draw_page)
        if expected_pages is not None and doc.page != expected_pages:
            raise ValueError(f"Expected {expected_pages} pages, generated {doc.page}.")
        staged_pdf.replace(output)
    return doc.page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "cv.json", help="JSON content file")
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "academic-cv.pdf", help="PDF output path")
    parser.add_argument("--expected-pages", type=int, help="fail if the PDF has a different page count")
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    page_count = build_pdf(data, args.output, args.expected_pages)
    print(f"Built {args.output} ({page_count} pages)")


if __name__ == "__main__":
    main()
