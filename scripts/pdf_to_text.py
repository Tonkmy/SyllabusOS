#!/usr/bin/env python3
"""
Extract text from PDF files using PyMuPDF.

Examples:
    uv run python scripts/pdf_to_text.py slides.pdf
    uv run python scripts/pdf_to_text.py slides.pdf -o slides.txt
    uv run python scripts/pdf_to_text.py slides.pdf -p 1-5
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pymupdf


def parse_page_range(page_spec: str, total_pages: int) -> range:
    if "-" in page_spec:
        start_text, end_text = page_spec.split("-", 1)
        start = max(int(start_text) - 1, 0)
        end = min(int(end_text), total_pages)
        return range(start, end)
    page = int(page_spec) - 1
    if 0 <= page < total_pages:
        return range(page, page + 1)
    return range(0, 0)


def extract_text(pdf_path: Path, pages: str | None) -> str:
    document = pymupdf.open(pdf_path)
    page_range = parse_page_range(pages, len(document)) if pages else range(len(document))
    chunks: list[str] = []
    for index in page_range:
        page_text = document[index].get_text()
        if page_text.strip():
            chunks.append(page_text)
    document.close()
    return "\n".join(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", help="path to the PDF file")
    parser.add_argument("-o", "--output", help="optional output text file")
    parser.add_argument("-p", "--pages", help="page range like 1-5 or 3")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    if not pdf_path.is_file():
        raise SystemExit(f"PDF not found: {pdf_path}")

    text = extract_text(pdf_path, args.pages)
    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.write_text(text, encoding="utf-8")
        print(f"wrote {output_path}")
    else:
        print(text)


if __name__ == "__main__":
    main()
