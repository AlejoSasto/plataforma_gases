"""Manual de Vigía en PDF, para la tesis y para la mina."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

from app.modules.assistant.manual_index import _split_frontmatter, load_sections

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "manual"
OUT = ROOT / "docs" / "manual" / "manual_vigia.pdf"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover": ParagraphStyle("Cover", parent=base["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26),
        "h1": ParagraphStyle("H1m", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=14, spaceBefore=12),
        "body": ParagraphStyle("Bm", parent=base["Normal"], fontName="Helvetica", fontSize=10, leading=14),
    }


def build(out: Path = OUT) -> Path:
    styles = _styles()
    story = [
        Paragraph("Vigía", styles["cover"]),
        Paragraph("Manual de uso. Gases en la mina.", styles["body"]),
        Spacer(1, 1 * cm),
        Paragraph("Índice", styles["h1"]),
    ]
    sections = load_sections(MANUAL)
    seen: list[str] = []
    for section in sections:
        if section.title in seen:
            continue
        seen.append(section.title)
        story.append(Paragraph(section.title, styles["body"]))
    story.append(PageBreak())
    written: set[str] = set()
    for path in sorted(MANUAL.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        _meta, body = _split_frontmatter(raw)
        if path.stem in written:
            continue
        written.add(path.stem)
        for line in body.splitlines():
            image = None
            if line.strip().startswith("!["):
                start = line.find("](")
                end = line.rfind(")")
                if start > 0 and end > start:
                    image = line[start + 2 : end]
            if line.startswith("# "):
                story.append(Paragraph(line[2:], styles["h1"]))
            elif line.startswith("## "):
                story.append(Paragraph(line[3:], styles["h1"]))
            elif image:
                img_path = (path.parent / image).resolve()
                if img_path.is_file():
                    story.append(Image(str(img_path), width=14 * cm, height=8 * cm, kind="proportional"))
            elif line.strip():
                story.append(Paragraph(line.replace("&", "&amp;"), styles["body"]))
        story.append(Spacer(1, 0.4 * cm))
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out), pagesize=A4, title="Manual de Vigía")
    doc.build(story)
    return out


if __name__ == "__main__":
    print(build())
