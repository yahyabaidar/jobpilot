import io

from django.utils import timezone
from django.utils.text import slugify
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

MARGIN = 22 * mm
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _company_slug(job_offer) -> str:
    return slugify(job_offer.company or job_offer.title or "entreprise") or "entreprise"


def letter_pdf_filename(letter) -> str:
    date_str = timezone.localdate().isoformat()
    return f"jobpilot_lettre_{_company_slug(letter.job_offer)}_{date_str}.pdf"


def tailored_cv_pdf_filename(tailored_cv) -> str:
    date_str = timezone.localdate().isoformat()
    return f"jobpilot_cv_{_company_slug(tailored_cv.job_offer)}_{date_str}.pdf"


class _PageWriter:
    """Small helper to lay out sober, single-column text with automatic page breaks."""

    def __init__(self, c: canvas.Canvas):
        self.c = c
        self.width, self.height = A4
        self.y = self.height - MARGIN
        self.c.setFont(FONT, 10)

    def _new_page(self) -> None:
        self.c.showPage()
        self.c.setFont(FONT, 10)
        self.y = self.height - MARGIN

    def heading(self, text: str, size: int = 14) -> None:
        if self.y < MARGIN + 15 * mm:
            self._new_page()
        self.c.setFont(FONT_BOLD, size)
        self.c.drawString(MARGIN, self.y, text)
        self.y -= (size / 2) * mm + 4 * mm
        self.c.setFont(FONT, 10)

    def subheading(self, text: str) -> None:
        if self.y < MARGIN + 10 * mm:
            self._new_page()
        self.c.setFont(FONT_BOLD, 10.5)
        self.c.drawString(MARGIN, self.y, text)
        self.y -= 5.5 * mm
        self.c.setFont(FONT, 10)

    def paragraph(self, text: str, size: int = 10, leading: float = 5 * mm) -> None:
        self.c.setFont(FONT, size)
        max_width = self.width - 2 * MARGIN
        for raw_line in text.split("\n"):
            if not raw_line.strip():
                self.y -= leading
                continue
            for line in simpleSplit(raw_line, FONT, size, max_width):
                if self.y < MARGIN:
                    self._new_page()
                    self.c.setFont(FONT, size)
                self.c.drawString(MARGIN, self.y, line)
                self.y -= leading

    def spacer(self, height: float = 4 * mm) -> None:
        self.y -= height


def render_letter_pdf(letter) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    writer = _PageWriter(c)

    candidate_name = letter.user.get_full_name() or letter.user.email
    writer.heading(candidate_name, size=13)
    writer.paragraph(letter.user.email, size=9)
    writer.spacer(6 * mm)

    writer.subheading(f"Candidature — {letter.job_offer.title}")
    if letter.job_offer.company:
        writer.paragraph(letter.job_offer.company, size=9)
    writer.spacer(6 * mm)

    writer.paragraph(letter.content or "", size=10, leading=5.2 * mm)

    c.showPage()
    c.save()
    return buffer.getvalue()


def render_tailored_cv_pdf(tailored_cv) -> bytes:
    content = tailored_cv.content or {}
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    writer = _PageWriter(c)

    candidate_name = tailored_cv.user.get_full_name() or tailored_cv.user.email
    writer.heading(candidate_name, size=15)
    if content.get("titre"):
        writer.paragraph(content["titre"], size=11)
    writer.paragraph(tailored_cv.user.email, size=9)
    writer.spacer(6 * mm)

    if content.get("resume"):
        writer.subheading("Résumé")
        writer.paragraph(content["resume"])
        writer.spacer(4 * mm)

    if content.get("competences"):
        writer.subheading("Compétences")
        writer.paragraph(", ".join(content["competences"]))
        writer.spacer(4 * mm)

    if content.get("experiences"):
        writer.subheading("Expériences")
        for exp in content["experiences"]:
            title_line = exp.get("poste", "")
            if exp.get("entreprise"):
                title_line += f" — {exp['entreprise']}"
            writer.paragraph(title_line, size=10)
            if exp.get("description"):
                writer.paragraph(exp["description"], size=9.5, leading=4.5 * mm)
            writer.spacer(3 * mm)

    c.showPage()
    c.save()
    return buffer.getvalue()
