import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _configure_tesseract_binary(pytesseract_module):
    """Configure tesseract executable path for Windows and env overrides."""
    configured_cmd = os.environ.get('TESSERACT_CMD', '').strip()
    if configured_cmd:
        pytesseract_module.pytesseract.tesseract_cmd = configured_cmd
        return

    default_windows_cmd = Path('C:/Program Files/Tesseract-OCR/tesseract.exe')
    if os.name == 'nt' and default_windows_cmd.exists():
        pytesseract_module.pytesseract.tesseract_cmd = str(default_windows_cmd)


def extract_text_from_file(file_path):
    """
    Extract text from a document file using pytesseract (for images)
    or pdfplumber (for PDFs).

    Args:
        file_path (str): Absolute path to the uploaded file.

    Returns:
        str: Extracted text, or empty string on failure.
    """
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == '.pdf':
            return _extract_from_pdf(file_path)
        elif ext in ('.jpg', '.jpeg', '.png'):
            return _extract_from_image(file_path)
        else:
            logger.warning("Unsupported file extension for OCR: %s", ext)
            return ''
    except Exception as e:
        logger.error("OCR extraction failed for %s: %s", file_path, str(e))
        return ''


def _extract_from_image(file_path):
    """Use pytesseract to extract text from JPG/PNG images."""
    try:
        import pytesseract
        from PIL import Image

        _configure_tesseract_binary(pytesseract)

        image = Image.open(file_path)
        # Convert to RGB to handle RGBA/palette images
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')

        text = pytesseract.image_to_string(image, lang='eng')
        return text.strip()
    except ImportError:
        logger.error("pytesseract or Pillow is not installed.")
        return '[OCR unavailable: pytesseract/Pillow not installed]'
    except Exception as e:
        logger.error("Image OCR failed: %s", str(e))
        return ''


def _extract_from_pdf(file_path):
    """
    Extract text from PDF.
    First tries pdfplumber (direct text extraction for text-based PDFs).
    Falls back to pytesseract (OCR) for scanned/image-only PDFs.
    """
    text = ''

    # --- Attempt 1: Direct text extraction with pdfplumber ---
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            pages_text = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
            text = '\n\n'.join(pages_text).strip()

        if len(text) > 50:   # Non-trivial text found
            return text
    except ImportError:
        logger.warning("pdfplumber not installed, skipping direct PDF text extraction.")
    except Exception as e:
        logger.warning("pdfplumber extraction failed: %s", str(e))

    # --- Attempt 2: OCR fallback for scanned PDFs ---
    try:
        import pytesseract
        from PIL import Image
        import fitz  # PyMuPDF

        _configure_tesseract_binary(pytesseract)

        doc = fitz.open(file_path)
        ocr_pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render page at 200 DPI for good OCR quality
            mat = fitz.Matrix(200 / 72, 200 / 72)
            clip = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [clip.width, clip.height], clip.samples)
            page_text = pytesseract.image_to_string(img, lang='eng')
            if page_text.strip():
                ocr_pages.append(page_text.strip())
        doc.close()
        text = '\n\n'.join(ocr_pages).strip()
        return text

    except ImportError:
        logger.error("PyMuPDF (fitz) or pytesseract not installed for PDF OCR fallback.")
        return text  # Return whatever we got from pdfplumber (possibly empty)
    except Exception as e:
        logger.error("PDF OCR fallback failed: %s", str(e))
        return text
