import os
import qrcode
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def generate_qr_image(url: str, save_path: str):
    img = qrcode.make(url)
    img.save(save_path)


def generate_tables_pdf(restaurant_name, tables, base_url, out_path):
    """Her masa için A4 üzerinde 2x3 QR kodlu sayfa üretir."""
    c = canvas.Canvas(out_path, pagesize=A4)
    width, height = A4

    cols, rows = 2, 3
    cell_w = width / cols
    cell_h = height / rows

    for idx, t in enumerate(tables):
        col = idx % cols
        row = (idx // cols) % rows
        x = col * cell_w
        y = height - (row + 1) * cell_h

        url = f"{base_url}/m/{t.qr_token}"
        qr_img = qrcode.make(url)
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)

        img_size = min(cell_w, cell_h) * 0.55
        c.drawImage(
            ImageReader(buf),
            x + (cell_w - img_size) / 2,
            y + cell_h - img_size - 1.2 * cm,
            img_size, img_size,
        )

        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(x + cell_w / 2, y + cell_h - img_size - 1.9 * cm, restaurant_name)
        c.setFont("Helvetica", 12)
        c.drawCentredString(x + cell_w / 2, y + cell_h - img_size - 2.5 * cm, f"Masa {t.number}")
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(x + cell_w / 2, y + 0.6 * cm, "Menü için QR kodu okutun")

        if (idx + 1) % (cols * rows) == 0 and idx + 1 < len(tables):
            c.showPage()

    c.save()