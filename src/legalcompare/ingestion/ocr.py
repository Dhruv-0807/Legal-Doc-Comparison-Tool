"""Step 2: OCR fallback for scanned/image PDF pages.

We use Tesseract (via pytesseract). Tesseract is a *system binary*, not a Python
package, so it may be absent. Everything here degrades gracefully: callers check
`tesseract_available()` first and we never crash the pipeline just because OCR
isn't installed — we surface it instead.
"""

from __future__ import annotations

import functools


@functools.lru_cache(maxsize=1)
def tesseract_available() -> bool:
    """True if the Tesseract binary is installed and reachable."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_image(image, lang: str = "eng") -> str:  # noqa: ANN001 - PIL.Image
    """Extract text from a single page image via Tesseract.

    Returns "" if OCR is unavailable rather than raising, so a missing binary
    degrades to "no text from this page" instead of a hard failure.
    """
    if not tesseract_available():
        return ""
    import pytesseract

    return pytesseract.image_to_string(image, lang=lang).strip()
