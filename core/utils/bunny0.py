# core/utils/pdf_utils.py
import io
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm

def _make_watermark_bytes(text: str):
    """
    ReportLab ile saydam watermark PDF'i (tek sayfa) bayt olarak üret.
    Tüm sayfalara merge edeceğiz.
    """
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    c.setFont("Helvetica", 10)
    c.setFillGray(0.4, 0.2)  # gri ve biraz şeffaf
    c.saveState()
    c.translate(300, 400)
    c.rotate(35)
    c.drawString(-200, 0, text)
    c.restoreState()
    c.showPage()
    c.save()
    packet.seek(0)
    return packet.read()

def personalize_pdf(source_fp, out_fp, watermark_text: str, open_password: str):
    """
    source_fp: input pdf file-like or path
    out_fp: output file-like or path
    watermark_text: e.g. "Licensed to volkan@example.com | 2025-10-26 10:12"
    open_password: PDF'i açma şifresi (license_password)
    """
    watermark_bytes = _make_watermark_bytes(watermark_text)

    wm_reader = PdfReader(io.BytesIO(watermark_bytes))
    wm_page = wm_reader.pages[0]

    reader = PdfReader(source_fp)
    writer = PdfWriter()

    for page in reader.pages:
        page.merge_page(wm_page)  # PyPDF2 >=3.0 için merge_page
        writer.add_page(page)

    # Şifrele
    writer.encrypt(user_password=open_password, owner_password=open_password)

    if hasattr(out_fp, "write"):
        writer.write(out_fp)
    else:
        with open(out_fp, "wb") as f:
            writer.write(f)

def build_watermark_text(email: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"Licensed to {email} | Generated at {ts}"
