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
    Image,
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
    "affiliation": ParagraphStyle("affiliation", fontName="CV", fontSize=11, leading=14, textColor=TEXT, spaceAfter=7),
    "intro": ParagraphStyle("intro", fontName="CV", fontSize=11, leading=14, textColor=TEXT, spaceAfter=7),
    "section": ParagraphStyle("section", fontName="CVBold", fontSize=15, leading=17.5, textColor=GREEN),
    "entry": ParagraphStyle("entry", fontName="CVBold", fontSize=11, leading=12.8, textColor=INK),
    "date": ParagraphStyle("date", alignment=TA_RIGHT, fontName="CV", fontSize=9.3, leading=12, textColor=MUTED),
    "detail": ParagraphStyle("detail", fontName="CV", fontSize=10.2, leading=11.8, textColor=TEXT),
    "paper_title": ParagraphStyle("paper_title", fontName="CVBold", fontSize=10.8, leading=12.9, textColor=INK),
    "paper_metadata": ParagraphStyle("paper_metadata", fontName="CV", fontSize=9.8, leading=12.2, textColor=MUTED),
    "award": ParagraphStyle("award", fontName="CV", fontSize=9.65, leading=12.2, textColor=TEXT),
}
CHINESE_STYLES = {
    name: ParagraphStyle(
        name + "-zh",
        parent=style,
        fontName="CVChineseBold" if style.fontName == "CVBold" else "CVChinese",
        wordWrap=None if name == "paper_title" else "CJK",
    )
    for name, style in STYLES.items()
}
LABELS = {
    "en": {
        "title": "Academic CV",
        "subject": "Academic curriculum vitae",
        "about": "About Me",
        "research": "Research interests",
        "wechat": "WeChat official accounts",
    },
    "zh": {
        "title": "学术简历",
        "subject": "学术简历",
        "about": "个人简介",
        "research": "研究方向",
        "wechat": "微信公众号",
    },
}


def chinese_content(value):
    """Use optional _zh overrides while sharing authors, links, and assets."""
    if isinstance(value, list):
        return [chinese_content(item) for item in value]
    if isinstance(value, dict):
        return {
            key: chinese_content(value.get(key + "_zh", item))
            for key, item in value.items()
            if not key.endswith("_zh")
        }
    return value


class Divider(Flowable):
    def __init__(self):
        super().__init__()
        self.width = CONTENT_WIDTH
        self.height = 1

    def draw(self):
        self.canv.setStrokeColor(colors.HexColor(RULE))
        self.canv.setLineWidth(0.65)
        self.canv.line(0, 0, self.width, 0)


def paragraph(markup, style, styles):
    return Paragraph(markup, styles[style])


def linked_label(label, url=None):
    if url:
        return f'<link href="{escape(url)}" color="{GREEN}">{escape(label)}</link>'
    return escape(label)


def heading(label, before, after, styles, content=()):
    return KeepTogether([
        Spacer(1, before),
        paragraph(escape(label), "section", styles),
        Spacer(1, 4),
        Divider(),
        Spacer(1, after),
        *content,
    ])


def entry(item, space, styles):
    title = paragraph(linked_label(item["title"], item.get("url")), "entry", styles)
    if date := item.get("date"):
        date_label = paragraph(escape(date), "date", styles)
        title = Table([[title, date_label]], colWidths=[CONTENT_WIDTH - 134, 134])
        title.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
    detail = "<br/>".join(escape(line) for line in item["details"])
    return KeepTogether([title, paragraph(detail, "detail", styles), Spacer(1, space)])


def publication(item, display_names, space, styles):
    title = linked_label(item["title"], item.get("url"))
    title_styles = STYLES if item["title"].isascii() else styles
    authors = []
    names = item.get("authors", [])
    for author in names:
        author_markup = escape(author)
        name = author.rstrip("†").strip()
        if name in display_names:
            author_markup = f"<b>{escape(name)}</b>{escape(author[len(name):])}"
        authors.append(author_markup)
    metadata = escape(item["status"])
    if authors:
        byline = ", ".join(authors)
        if styles is CHINESE_STYLES and all(name.rstrip("†").isascii() for name in names):
            byline = f'<font name="CV">{byline}</font>'
        metadata = f"{byline} · {metadata}"
    return KeepTogether([
        paragraph(title, "paper_title", title_styles),
        paragraph(metadata, "paper_metadata", styles),
        Spacer(1, space),
    ])


def award(item, space, styles):
    return KeepTogether([
        paragraph(f'{escape(item["title"])} · <b>{escape(item["result"])}</b>', "award", styles),
        Spacer(1, space),
    ])


def biography_paragraph(item, styles):
    text = item["text"]
    if isinstance(text, list):
        markup = "".join(linked_label(part["label"], part.get("url")) for part in text)
    else:
        markup = escape(text)
    if title := item.get("heading"):
        markup = f"<b>{escape(title)}</b><br/>{markup}"
        return paragraph(markup, "intro", styles)
    intro = styles["intro"]
    return Paragraph(markup, ParagraphStyle("bio-prose", parent=intro, firstLineIndent=2 * intro.fontSize))


def wechat_account_row(items, assets_dir, styles):
    qr_size = 60
    qr_column_width = qr_size + 7
    label_width = CONTENT_WIDTH / len(items) - qr_column_width
    cells = []
    for item in items:
        title = escape(item["title"])
        if item.get("language") == "zh":
            title = f'<font name="CVChinese">{title}</font>'
        qr_image = Image(str(assets_dir / item["qr_image"]), width=qr_size, height=qr_size)
        label = [
            paragraph(title, "entry", styles),
            paragraph(escape(item["description"]), "detail", styles),
        ]
        cells.extend([qr_image, label])
    return Table(
        [cells],
        colWidths=[qr_column_width, label_width] * len(items),
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )


def build_story(data, assets_dir=ROOT, *, language="en"):
    styles = STYLES if language == "en" else CHINESE_STYLES
    labels = LABELS[language]
    profile = data["profile"]
    name_markup = escape(profile["name"])
    display_names = {profile["name"]}
    if alternate_name := profile.get("alternate_name"):
        display_names.add(alternate_name)
        alternate_font = "CVChinese" if language == "en" else "CV"
        name_markup += (
            f' <font name="{alternate_font}" size="20" color="{GREEN}">'
            f'{escape(alternate_name)}</font>'
        )
    affiliation = escape(profile["affiliation"])
    if website := profile.get("website"):
        affiliation += " · " + linked_label(website["label"], website["url"])
    for field, label in (("arxiv", "arXiv"), ("linkedin", "LinkedIn")):
        if url := profile.get(field):
            affiliation += " · " + linked_label(label, url)
    story = [
        paragraph(name_markup, "name", styles),
        Spacer(1, 4),
        paragraph(affiliation, "affiliation", styles),
    ]
    if biography := profile.get("biography"):
        first, *remaining = biography
        story.append(heading(labels["about"], 2, 5, styles, [biography_paragraph(first, styles)]))
        story.extend(biography_paragraph(item, styles) for item in remaining)
    elif interests := profile.get("research_interests"):
        story.append(paragraph(f'<b>{labels["research"]}</b> · {escape(interests)}', "intro", styles))
    for section in data["sections"]:
        starts_page = section.get("new_page", False)
        if starts_page:
            story.append(PageBreak())
        kind = section["kind"]
        before = 4 if starts_page else 5
        after = 4
        if kind == "awards":
            before, after = 8, 5
        story.append(heading(section["title"], before, after, styles))
        if kind == "entries":
            space = section.get("entry_spacing", 2)
            story.extend(entry(item, space, styles) for item in section["items"])
        elif kind == "publications":
            space = section.get("entry_spacing", 6.7)
            story.extend(publication(item, display_names, space, styles) for item in section["items"])
        elif kind == "awards":
            space = section.get("entry_spacing", 3.7)
            story.extend(award(item, space, styles) for item in section["items"])
        else:
            raise ValueError(f"Unknown section kind: {kind}")
        if note := section.get("note"):
            story.append(paragraph(escape(note), "paper_metadata", styles))
    if footer := data.get("closing_note"):
        story.append(Spacer(1, 6))
        story.append(paragraph(
            f'<b>{escape(footer["label"])}</b> · {escape(footer["text"])}', "detail", styles
        ))
    if accounts := data.get("wechat_accounts"):
        account_row = wechat_account_row(accounts, assets_dir, styles)
        story.append(heading(labels["wechat"], 5, 4, styles, [account_row]))
    return story


def build_pdf(data, output, expected_pages, assets_dir=ROOT, *, language="en"):
    chinese = language == "zh"
    fonts = ensure_fonts(ROOT / "build" / "fonts", chinese_bold=chinese)
    faces = [
        ("CV", "Carlito-Regular.ttf"),
        ("CVBold", "Carlito-Bold.ttf"),
        ("CVChinese", "NotoSansSC-Regular.ttf"),
    ]
    if chinese:
        faces.append(("CVChineseBold", "NotoSansSC-Bold.ttf"))
        data = chinese_content(data)
    for name, filename in faces:
        pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    pdfmetrics.registerFontFamily("CV", normal="CV", bold="CVBold")
    if chinese:
        pdfmetrics.registerFontFamily("CVChinese", normal="CVChinese", bold="CVChineseBold")

    name = data["profile"]["name"]
    labels = LABELS[language]
    regular_font = "CVChinese" if chinese else "CV"
    bold_font = "CVChineseBold" if chinese else "CVBold"

    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(GREEN))
        canvas.rect(MARGIN, PAGE_HEIGHT - 40, 28, 2.1, fill=1, stroke=0)
        if doc.page > 1:
            canvas.setFont(bold_font, 10)
            canvas.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 41, name)
        canvas.setStrokeColor(colors.HexColor(RULE))
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN, 34, PAGE_WIDTH - MARGIN, 34)
        canvas.setFont(regular_font, 9)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(MARGIN, 21, f'{name} · {labels["title"]}')
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
            title=f'{name} | {labels["title"]}',
            author=name,
            subject=labels["subject"],
            invariant=1,
        )
        doc.build(
            build_story(data, assets_dir, language=language),
            onFirstPage=draw_page,
            onLaterPages=draw_page,
        )
        if expected_pages is not None and doc.page != expected_pages:
            raise ValueError(f"Expected {expected_pages} pages, generated {doc.page}.")
        staged_pdf.replace(output)
    return doc.page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "cv.json", help="JSON content file")
    parser.add_argument("--language", choices=("en", "zh"), default="en", help="PDF language")
    parser.add_argument("--output", type=Path, help="PDF output path")
    parser.add_argument("--expected-pages", type=int, help="fail if the PDF has a different page count")
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    default_name = "academic-cv-zh.pdf" if args.language == "zh" else "academic-cv.pdf"
    output = args.output or ROOT / "build" / default_name
    page_count = build_pdf(
        data, output, args.expected_pages, args.data.resolve().parent, language=args.language
    )
    print(f"Built {output} ({page_count} pages)")


if __name__ == "__main__":
    main()
