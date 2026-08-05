"""Printable QR plant labels (PDF)."""

from __future__ import annotations

from pathlib import Path

import segno
from fpdf import FPDF

from app.core.config import get_settings
from app.modules.plants.models import Plant


def build_labels_pdf(plants: list[Plant], *, public_base_url: str | None = None) -> bytes:
    settings = get_settings()
    base = (public_base_url or settings.public_base_url).rstrip("/")

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)

    # 2 columns x 5 rows of labels roughly
    col_w, row_h = 95, 50
    margin_x, margin_y = 10, 15
    cols, rows = 2, 5

    tmp_dir = Path(settings.media_root) / "_tmp_labels"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    qr_paths: list[Path] = []

    try:
        for index, plant in enumerate(plants):
            if index % (cols * rows) == 0:
                pdf.add_page()

            cell = index % (cols * rows)
            col = cell % cols
            row = cell // cols
            x = margin_x + col * col_w
            y = margin_y + row * row_h

            url = f"{base}/plants/{plant.id}"
            qr = segno.make(url, error="m")
            qr_path = tmp_dir / f"{plant.id}.png"
            qr.save(str(qr_path), scale=4, border=1)
            qr_paths.append(qr_path)

            pdf.image(str(qr_path), x=x, y=y, w=28, h=28)
            pdf.set_xy(x + 32, y + 2)
            pdf.set_font("Helvetica", "B", 11)
            name = (plant.nickname or "Plant")[:40]
            pdf.multi_cell(col_w - 36, 5, name)
            pdf.set_x(x + 32)
            pdf.set_font("Helvetica", "I", 8)
            sci = ""
            if plant.taxon is not None:
                sci = (plant.taxon.scientific_name or "")[:48]
            pdf.multi_cell(col_w - 36, 4, sci or "-")
            pdf.set_x(x + 32)
            pdf.set_font("Helvetica", "", 7)
            pdf.multi_cell(col_w - 36, 4, str(plant.id)[:18] + "...")

        out = pdf.output()
        if isinstance(out, (bytes, bytearray)):
            return bytes(out)
        return str(out).encode("latin-1")
    finally:
        for p in qr_paths:
            p.unlink(missing_ok=True)
