from __future__ import annotations

import os
from pathlib import Path
from shutil import which

from ..config import ExtractionConfig
from ..models import AttemptStatus, PageContext
from .base import ExtractionMethod


class TesseractOcrExtractor(ExtractionMethod):
    name = "ocr_tesseract"

    def resolve_tesseract_executable(self, config: ExtractionConfig) -> Path | None:
        configured = config.tesseract_executable
        if configured:
            resolved = Path(configured).expanduser()
            if resolved.is_file():
                return resolved

        env_value = os.environ.get("TESSERACT_CMD")
        if env_value:
            resolved = Path(env_value).expanduser()
            if resolved.is_file():
                return resolved

        for candidate in ("tesseract", "tesseract.exe"):
            resolved_name = which(candidate)
            if resolved_name:
                return Path(resolved_name)

        return None

    def is_available(self, config: ExtractionConfig) -> bool:
        try:
            import pytesseract  # type: ignore  # noqa: F401
        except Exception:
            return False
        return self.resolve_tesseract_executable(config) is not None

    def _render_page(self, page: PageContext, dpi: int) -> Path:
        try:
            import fitz  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"PyMuPDF is required for OCR rendering: {exc}") from exc

        pixmap_scale = dpi / 72.0
        matrix = fitz.Matrix(pixmap_scale, pixmap_scale)
        with fitz.open(str(page.source_path)) as doc:
            pdf_page = doc[page.page_number - 1]
            pixmap = pdf_page.get_pixmap(matrix=matrix, alpha=False)
        image_path = page.render_dir / f"page_{page.page_number:04d}.png"
        pixmap.save(str(image_path))
        return image_path

    def extract(self, page: PageContext, config: ExtractionConfig):
        tesseract_cmd = self.resolve_tesseract_executable(config)
        if tesseract_cmd is None:
            return self._build_attempt(
                status=AttemptStatus.SKIPPED,
                reason="tesseract_unavailable",
            )

        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
        except Exception as exc:
            return self._build_attempt(
                status=AttemptStatus.SKIPPED,
                reason="pytesseract_unavailable",
                error=str(exc),
            )

        try:
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_cmd)
            image_path = self._render_page(page, config.page_render_dpi)
            image = Image.open(image_path)
            cropped_image, crop_box = _prepare_ocr_image(image)
            if crop_box is not None:
                cropped_path = page.render_dir / f"page_{page.page_number:04d}_ocr_crop.png"
                cropped_image.save(str(cropped_path))
            text = pytesseract.image_to_string(cropped_image)
            return self._build_attempt(
                text=text,
                status=AttemptStatus.SUCCESS if text.strip() else AttemptStatus.FAILED,
                reason="ocr_text_extracted" if text.strip() else "empty_ocr_output",
                artifact_path=image_path,
            )
        except Exception as exc:
            return self._build_attempt(
                status=AttemptStatus.FAILED,
                reason="ocr_failed",
                error=str(exc),
            )


def _prepare_ocr_image(image, padding: int = 20, threshold: int = 245):
    try:
        from PIL import Image  # type: ignore  # noqa: F401
    except Exception as exc:
        raise RuntimeError(f"Pillow is required for OCR preprocessing: {exc}") from exc

    grayscale = image.convert("L")
    mask = grayscale.point(lambda pixel: 255 if pixel < threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return grayscale, None

    left, top, right, bottom = bbox
    width, height = grayscale.size
    crop_box = (
        max(0, left - padding),
        max(0, top - padding),
        min(width, right + padding),
        min(height, bottom + padding),
    )
    return grayscale.crop(crop_box), crop_box
