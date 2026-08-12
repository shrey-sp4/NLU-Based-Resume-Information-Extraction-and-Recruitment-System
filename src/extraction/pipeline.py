from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .models import utc_now_iso

from .audit import (
    write_document_result,
    write_page_result,
    write_review_queue,
    write_run_manifest,
)
from .config import ExtractionConfig, build_default_config
from .discovery import build_document_sources, build_run_manifest, discover_pdf_files
from .models import (
    AttemptStatus,
    DocumentExtractionResult,
    DocumentStatus,
    ExtractionAttempt,
    PageContext,
    PageExtractionResult,
    PageStatus,
)
from .output import build_document_directory, build_page_directory, build_render_directory, build_run_directory
from .preflight import preflight_pdf
from .validation import ValidationDecision, evaluate_text, normalize_text
from .methods.layout import LayoutAwarePdfPlumberExtractor
from .methods.native import PyMuPdfNativeExtractor, PypdfNativeExtractor
from .methods.ocr import TesseractOcrExtractor
from .methods.poppler import PopplerTextExtractor


class ExtractionPipeline:
    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or build_default_config()
        self.methods = self._build_methods()

    def _build_methods(self):
        available = {
            "native_pymupdf": PyMuPdfNativeExtractor(),
            "native_pypdf": PypdfNativeExtractor(),
            "layout_pdfplumber": LayoutAwarePdfPlumberExtractor(),
            "poppler_text": PopplerTextExtractor(),
            "ocr_tesseract": TesseractOcrExtractor(),
        }
        ordered = []
        for name in self.config.method_order:
            method = available.get(name)
            if method is not None:
                ordered.append(method)
        return ordered

    def discover(self) -> List[Path]:
        return discover_pdf_files(self.config.input_root)

    def run(self) -> Path:
        pdf_paths = self.discover()
        document_sources = build_document_sources(pdf_paths)
        manifest = build_run_manifest(self.config, document_sources)
        run_dir = build_run_directory(manifest.output_root.parent, manifest.run_id)
        write_run_manifest(run_dir, manifest)

        review_rows: List[Dict[str, object]] = []
        for document_source in document_sources:
            document_dir = build_document_directory(run_dir, document_source.document_id)
            result = self._process_document(document_source, document_dir)
            write_document_result(document_dir, result)
            for page in result.pages:
                page_dir = build_page_directory(document_dir, page.page_number)
                write_page_result(page_dir, page)
                if page.status == PageStatus.REVIEW:
                    review_rows.append(
                        {
                            "document_id": document_source.document_id,
                            "source_path": str(document_source.source_path),
                            "page_number": page.page_number,
                            "page_status": page.status.value,
                            "review_reason": page.review_reason,
                            "final_method": page.final_method,
                        }
                    )

            if result.status == DocumentStatus.REVIEW:
                review_rows.append(
                    {
                        "document_id": document_source.document_id,
                        "source_path": str(document_source.source_path),
                        "page_number": None,
                        "page_status": result.status.value,
                        "review_reason": result.review_reason,
                        "final_method": None,
                    }
                )

        if review_rows:
            write_review_queue(run_dir, review_rows)

        return run_dir

    def _process_document(
        self,
        document_source,
        document_dir: Path,
    ) -> DocumentExtractionResult:
        started_at = utc_now_iso()
        preflight = preflight_pdf(document_source.source_path)
        page_count = preflight.page_count
        pages: List[PageExtractionResult] = []

        if not preflight.readable or page_count is None or page_count < 1:
            return DocumentExtractionResult(
                document_id=document_source.document_id,
                source_path=document_source.source_path,
                file_hash=document_source.file_hash,
                file_size=document_source.file_size,
                page_count=page_count,
                status=DocumentStatus.REVIEW,
                pages=[],
                preflight=preflight,
                review_reason="preflight_failed" if not preflight.readable else "page_count_unavailable",
                started_at=started_at,
                finished_at=utc_now_iso(),
            )

        for page_number in range(1, page_count + 1):
            page_dir = build_page_directory(document_dir, page_number)
            render_dir = build_render_directory(page_dir)
            context = PageContext(
                document_id=document_source.document_id,
                source_path=document_source.source_path,
                page_number=page_number,
                page_count=page_count,
                document_dir=document_dir,
                page_dir=page_dir,
                render_dir=render_dir,
                preflight=preflight.to_dict(),
            )
            pages.append(self._process_page(context))

        status = DocumentStatus.PASS_
        review_reason = None
        for page in pages:
            if page.status == PageStatus.REVIEW:
                status = DocumentStatus.REVIEW
                review_reason = review_reason or page.review_reason or f"page_{page.page_number}_needs_review"

        return DocumentExtractionResult(
            document_id=document_source.document_id,
            source_path=document_source.source_path,
            file_hash=document_source.file_hash,
            file_size=document_source.file_size,
            page_count=page_count,
            status=status,
            pages=pages,
            preflight=preflight,
            review_reason=review_reason,
            started_at=started_at,
            finished_at=utc_now_iso(),
        )

    def _process_page(self, page: PageContext) -> PageExtractionResult:
        attempts: List[ExtractionAttempt] = []
        best_attempt: Optional[ExtractionAttempt] = None
        best_decision: Optional[ValidationDecision] = None
        review_reason: Optional[str] = None

        for method in self.methods:
            attempt = method.extract(page, self.config)
            attempts.append(attempt)
            if attempt.status == AttemptStatus.SKIPPED:
                continue

            decision = evaluate_text(attempt.text, self.config, page.page_number, page.page_count)
            if decision.accepted:
                best_attempt = attempt
                best_decision = decision
                break

            if best_attempt is None:
                best_attempt = attempt
                best_decision = decision
                review_reason = decision.reason

        if best_attempt and best_decision and best_decision.accepted:
            normalized_text = normalize_text(best_attempt.text)
            page_type_guess = self._guess_page_type(best_attempt, page)
            return PageExtractionResult(
                page_number=page.page_number,
                status=PageStatus.PASS_,
                final_method=best_attempt.method,
                final_text=normalized_text,
                metrics=best_decision.metrics,
                attempts=attempts,
                review_reason=None,
                page_type_guess=page_type_guess,
            )

        if best_attempt and best_decision:
            normalized_text = normalize_text(best_attempt.text)
            page_type_guess = self._guess_page_type(best_attempt, page)
            return PageExtractionResult(
                page_number=page.page_number,
                status=PageStatus.REVIEW,
                final_method=best_attempt.method,
                final_text=normalized_text,
                metrics=best_decision.metrics,
                attempts=attempts,
                review_reason=review_reason or best_decision.reason,
                page_type_guess=page_type_guess,
            )

        return PageExtractionResult(
            page_number=page.page_number,
            status=PageStatus.REVIEW,
            final_method=None,
            final_text="",
            metrics=evaluate_text("", self.config, page.page_number, page.page_count).metrics,
            attempts=attempts,
            review_reason="no_method_produced_text",
            page_type_guess="unknown",
        )

    def _guess_page_type(self, attempt: ExtractionAttempt, page: PageContext) -> str:
        preflight = page.preflight or {}
        if attempt.metrics.char_count == 0:
            return "blank_or_image_only"
        if attempt.method == "ocr_tesseract":
            return "scanned_or_image"
        if preflight.get("page_count") == 1:
            return "single_page_text"
        return "text"


def run_extraction(config: Optional[ExtractionConfig] = None) -> Path:
    return ExtractionPipeline(config).run()
