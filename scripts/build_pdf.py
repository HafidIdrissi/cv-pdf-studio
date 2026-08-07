#!/usr/bin/env python3
"""Compile and quality-check a LaTeX CV or cover letter PDF.

Exit codes:
    0  PDF built and all requested checks passed
    2  LaTeX compilation failed
    3  PDF exceeds --max-pages
    4  Invalid input, missing dependency, placeholder, photo, or unknown page count
    5  Extracted-text QA failed
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PLACEHOLDER_RE = re.compile(r"\{\{(?![\\{])[^{}]+?\}\}", re.DOTALL)


class InputError(RuntimeError):
    """Raised when a build input cannot be validated safely."""


def placeholder_labels(source: str) -> list[str]:
    """Return compact, unique placeholder labels from a LaTeX source."""
    labels: set[str] = set()
    for match in PLACEHOLDER_RE.findall(source):
        compact = " ".join(match.replace("\n", " ").split())
        labels.add(compact[:100] + ("..." if len(compact) > 100 else ""))
    return sorted(labels)


def is_jpeg(path: Path) -> bool:
    try:
        return path.read_bytes()[:3] == b"\xff\xd8\xff"
    except OSError:
        return False


def prepare_photo(src: Path, dest: Path, ratio: float = 3 / 4, width: int = 700) -> Path:
    """Center-crop a photo to ``ratio`` (w/h) and save a verified RGB JPEG."""
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        if is_jpeg(src):
            shutil.copyfile(src, dest)
            return dest
        raise InputError(
            "Pillow is required to convert non-JPEG photos; install it with 'pip install pillow'"
        ) from exc

    try:
        with Image.open(src) as opened:
            img = ImageOps.exif_transpose(opened).convert("RGB")
            w, h = img.size
            if w <= 0 or h <= 0:
                raise InputError("photo has invalid dimensions")
            if w / h > ratio:
                new_w = int(h * ratio)
                left = (w - new_w) // 2
                img = img.crop((left, 0, left + new_w, h))
            else:
                new_h = int(w / ratio)
                top = int((h - new_h) * 0.25)
                top = max(0, min(top, h - new_h))
                img = img.crop((0, top, w, top + new_h))
            height = int(width / ratio)
            resampling = getattr(Image, "Resampling", Image)
            img = img.resize((width, height), resampling.LANCZOS)
            img.save(dest, "JPEG", quality=92, optimize=True)
    except UnidentifiedImageError as exc:
        raise InputError(f"unreadable photo: {src}") from exc
    except OSError as exc:
        raise InputError(f"could not process photo {src}: {exc}") from exc
    return dest


def log_page_count(log_text: str) -> int | None:
    match = re.search(r"Output written on .*?\((\d+) pages?", log_text)
    return int(match.group(1)) if match else None


def page_count(pdf_path: Path, log_text: str, timeout: int = 30) -> int | None:
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        pass

    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        try:
            proc = subprocess.run(
                [pdfinfo, str(pdf_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            if proc.returncode == 0:
                match = re.search(r"^Pages:\s+(\d+)\s*$", proc.stdout, re.MULTILINE)
                if match:
                    return int(match.group(1))
        except (OSError, subprocess.TimeoutExpired):
            pass
    return log_page_count(log_text)


def extract_pdf_text(pdf_path: Path, timeout: int = 30) -> str | None:
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        try:
            proc = subprocess.run(
                [pdftotext, "-enc", "UTF-8", str(pdf_path), "-"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            if proc.returncode == 0:
                return proc.stdout
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages)
    except Exception:
        return None


def normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def text_qa(
    extracted: str,
    expect_text: list[str],
    expect_order: list[str],
    min_text_chars: int,
) -> list[str]:
    failures: list[str] = []
    normalized = normalized_text(extracted)
    if len(normalized) < min_text_chars:
        failures.append(
            f"extracted text is too short ({len(normalized)} characters; expected at least {min_text_chars})"
        )
    if placeholder_labels(extracted):
        failures.append("placeholder-like text remains in the extracted PDF")
    for expected in expect_text:
        if normalized_text(expected) not in normalized:
            failures.append(f"missing expected text: {expected!r}")
    cursor = 0
    for expected in expect_order:
        needle = normalized_text(expected)
        position = normalized.find(needle, cursor)
        if position < 0:
            failures.append(f"missing or out-of-order text: {expected!r}")
            break
        cursor = position + len(needle)
    return failures


def print_log_tail(log_text: str, lines: int = 40) -> None:
    print("\n".join(log_text.strip().splitlines()[-lines:]))


def copy_for_inspection(pdf: Path, out_dir: Path, base: str, suffix: str) -> Path:
    destination = out_dir / f"{base}.{suffix}.pdf"
    shutil.copyfile(pdf, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tex", required=True, type=Path, help="path to the .tex source")
    parser.add_argument("--photo", type=Path, help="optional design-CV photo")
    parser.add_argument("--out", type=Path, default=Path("outputs"), help="output directory")
    parser.add_argument("--max-pages", type=int, default=1, help="0 disables the page limit")
    parser.add_argument("--engine", default="pdflatex", choices=["pdflatex", "xelatex", "lualatex"])
    parser.add_argument("--keep-tex", action="store_true", help="copy the .tex next to a successful PDF")
    parser.add_argument("--check-text", action="store_true", help="require a readable PDF text layer")
    parser.add_argument("--expect-text", action="append", default=[], help="text that must appear; repeatable")
    parser.add_argument(
        "--expect-order",
        action="append",
        default=[],
        help="text fragments that must appear in the supplied order; repeatable",
    )
    parser.add_argument("--min-text-chars", type=int, default=120)
    parser.add_argument("--timeout", type=int, default=60, help="seconds allowed per external command")
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="testing only: compile a template that still contains placeholders",
    )
    args = parser.parse_args()

    tex = args.tex.expanduser().resolve()
    out_dir = args.out.expanduser().resolve()
    if not tex.is_file():
        print(f"ERROR: no such .tex file: {tex}")
        return 4
    if args.max_pages < 0:
        print("ERROR: --max-pages cannot be negative")
        return 4
    if args.min_text_chars < 0 or args.timeout <= 0:
        print("ERROR: --min-text-chars must be non-negative and --timeout must be positive")
        return 4
    engine = shutil.which(args.engine)
    if not engine:
        print(f"ERROR: LaTeX engine not found: {args.engine}")
        return 4

    try:
        source = tex.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: could not read UTF-8 LaTeX source: {exc}")
        return 4
    placeholders = placeholder_labels(source)
    if placeholders and not args.allow_placeholders:
        print(f"ERROR: {len(placeholders)} unresolved placeholder(s) remain:")
        for label in placeholders[:10]:
            print(f"  {label}")
        return 4

    if args.photo:
        photo = args.photo.expanduser().resolve()
        if not photo.is_file():
            print(f"ERROR: no such photo: {photo}")
            return 4
        if photo.suffix.lower() not in PHOTO_EXT:
            print(f"ERROR: unsupported image format: {photo.suffix or '(none)'}")
            return 4
    else:
        photo = None

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"ERROR: could not create output directory: {exc}")
        return 4

    base = tex.stem
    log_text = ""
    with tempfile.TemporaryDirectory(prefix="cv-pdf-studio-") as temp_name:
        build_dir = Path(temp_name)
        build_tex = build_dir / f"{base}.tex"
        shutil.copyfile(tex, build_tex)
        if photo:
            try:
                prepare_photo(photo, build_dir / "photo.jpg")
            except InputError as exc:
                print(f"ERROR: {exc}")
                return 4

        for pass_number in (1, 2):
            try:
                proc = subprocess.run(
                    [
                        engine,
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        "-file-line-error",
                        "-no-shell-escape",
                        build_tex.name,
                    ],
                    cwd=build_dir,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=args.timeout,
                )
            except subprocess.TimeoutExpired:
                print(f"LaTeX compilation FAILED: pass {pass_number} exceeded {args.timeout}s")
                return 2
            except OSError as exc:
                print(f"LaTeX compilation FAILED: {exc}")
                return 2
            log_text = proc.stdout + proc.stderr
            if proc.returncode != 0:
                print(f"LaTeX compilation FAILED on pass {pass_number}. Last log lines:\n")
                print_log_tail(log_text)
                return 2

        pdf = build_dir / f"{base}.pdf"
        if not pdf.is_file():
            print("LaTeX compilation FAILED: engine returned success but produced no PDF")
            print_log_tail(log_text)
            return 2

        pages = page_count(pdf, log_text, timeout=args.timeout)
        if pages is None or pages < 1:
            print("ERROR: page count could not be verified; PDF will not be delivered")
            return 4
        if args.max_pages and pages > args.max_pages:
            inspection = copy_for_inspection(pdf, out_dir, base, "over-limit")
            print(f"PAGE LIMIT EXCEEDED ({pages} > {args.max_pages})")
            print(f"Inspection PDF written: {inspection}")
            return 3

        should_check_text = args.check_text or args.expect_text or args.expect_order
        if should_check_text:
            extracted = extract_pdf_text(pdf, timeout=args.timeout)
            if extracted is None:
                print("TEXT QA FAILED: neither pdftotext nor pypdf could extract text")
                return 5
            failures = text_qa(
                extracted,
                expect_text=args.expect_text,
                expect_order=args.expect_order,
                min_text_chars=args.min_text_chars,
            )
            if failures:
                inspection = copy_for_inspection(pdf, out_dir, base, "qa-failed")
                print("TEXT QA FAILED:")
                for failure in failures:
                    print(f"  - {failure}")
                print(f"Inspection PDF written: {inspection}")
                return 5

        final = out_dir / f"{base}.pdf"
        shutil.copyfile(pdf, final)
        if args.keep_tex:
            shutil.copyfile(build_tex, out_dir / build_tex.name)

    print(f"PDF written: {final}")
    print(f"Pages: {pages}")
    if should_check_text:
        print("Text QA: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
