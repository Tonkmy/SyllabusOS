#!/usr/bin/env python3
"""
Convert Markdown workspace notes to styled PDFs with math support.

Examples:
    uv run python scripts/md_to_pdf.py "subjects/CSCI/ARIN5204 Reinforcement Learning"
    uv run python scripts/md_to_pdf.py "subjects/CSCI/ARIN5204 Reinforcement Learning" --files chapter01_intro.md
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import sys
from io import BytesIO
from pathlib import Path

import markdown
import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["mathtext.fontset"] = "cm"
import matplotlib.pyplot as plt


if sys.platform == "darwin":
    brew_lib = "/opt/homebrew/lib"
    current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if brew_lib not in current:
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = f"{brew_lib}:{current}" if current else brew_lib


PLACEHOLDER = "\x00MATH"


def build_css(course_name: str) -> str:
    return f"""
@page {{
    size: A4;
    margin: 2cm 2.1cm;
    @top-right {{
        content: "{course_name}";
        font-size: 9px;
        color: #666;
    }}
    @bottom-center {{
        content: "Page " counter(page) " / " counter(pages);
        font-size: 9px;
        color: #666;
    }}
}}

body {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.55;
    color: #1d1d1f;
}}

h1 {{
    color: #123a72;
    border-bottom: 3px solid #123a72;
    padding-bottom: 6px;
}}

h2 {{
    color: #1f4d8f;
    border-bottom: 1px solid #d8deea;
    padding-bottom: 4px;
    margin-top: 28px;
}}

h3 {{
    margin-top: 20px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 10pt;
}}

th, td {{
    border-bottom: 1px solid #d8deea;
    padding: 7px 9px;
    text-align: left;
}}

th {{
    background: #123a72;
    color: white;
}}

code {{
    background: #f3f6fa;
    padding: 1px 4px;
    border-radius: 3px;
}}

pre {{
    background: #f3f6fa;
    padding: 12px 14px;
    border-left: 4px solid #123a72;
    overflow-x: auto;
}}

blockquote {{
    border-left: 4px solid #6ca0dc;
    background: #eef5fd;
    padding: 8px 14px;
    color: #294057;
}}

.math-display {{
    text-align: center;
    margin: 16px 0;
}}

.math-display img {{
    max-width: 85%;
}}

.math-inline {{
    vertical-align: middle;
}}
"""


def latex_to_svg(latex: str, display: bool) -> str:
    try:
        fontsize = 14 if display else 11
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.patch.set_alpha(0.0)
        fig.text(0, 0, f"${latex}$", fontsize=fontsize, color="#1d1d1f")
        buf = BytesIO()
        fig.savefig(
            buf,
            format="svg",
            dpi=150,
            transparent=True,
            bbox_inches="tight",
            pad_inches=0.03,
        )
        plt.close(fig)
        buf.seek(0)
        payload = base64.b64encode(buf.read()).decode("utf-8")
        if display:
            return f'<div class="math-display"><img src="data:image/svg+xml;base64,{payload}"/></div>'
        return f'<img class="math-inline" src="data:image/svg+xml;base64,{payload}"/>'
    except Exception:
        delim = "$$" if display else "$"
        return f"<code>{delim}{latex}{delim}</code>"


def convert_math(md_text: str) -> tuple[str, list[str]]:
    fragments: list[str] = []

    def stash(fragment: str) -> str:
        index = len(fragments)
        fragments.append(fragment)
        return f"{PLACEHOLDER}{index}\x00"

    md_text = re.sub(
        r"\$\$(.+?)\$\$",
        lambda match: stash(latex_to_svg(match.group(1).strip(), display=True)),
        md_text,
        flags=re.DOTALL,
    )
    md_text = re.sub(
        r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)",
        lambda match: stash(latex_to_svg(match.group(1).strip(), display=False)),
        md_text,
    )
    return md_text, fragments


def restore_math(html: str, fragments: list[str]) -> str:
    return re.sub(rf"{PLACEHOLDER}(\d+)\x00", lambda match: fragments[int(match.group(1))], html)


def md_to_html(md_text: str, course_name: str) -> str:
    md_text, fragments = convert_math(md_text)
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
    )
    html_body = restore_math(html_body, fragments)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<style>{build_css(course_name)}</style>
</head>
<body>
{html_body}
</body>
</html>"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("course_dir", help="path to the workspace directory")
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="specific markdown files under notes/chapters/",
    )
    return parser.parse_args()


def resolve_targets(course_dir: Path, requested: list[str] | None) -> list[Path]:
    notes_dir = course_dir / "notes" / "chapters"
    if requested:
        return [notes_dir / name for name in requested]
    return sorted(notes_dir.glob("*.md"))


def main() -> None:
    args = parse_args()
    course_dir = Path(args.course_dir).resolve()
    if not course_dir.is_dir():
        raise SystemExit(f"workspace directory not found: {course_dir}")

    try:
        from weasyprint import HTML
    except Exception as exc:
        raise SystemExit(
            "weasyprint is not available. Run `uv sync` and ensure required system libraries are installed."
        ) from exc

    targets = resolve_targets(course_dir, args.files)
    if not targets:
        raise SystemExit(f"no markdown files found under {course_dir / 'notes' / 'chapters'}")

    export_dir = course_dir / "notes" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    for md_path in targets:
        if not md_path.exists():
            print(f"skip: {md_path.name} not found")
            continue
        html = md_to_html(md_path.read_text(encoding="utf-8"), course_dir.name)
        pdf_path = export_dir / f"{md_path.stem}.pdf"
        HTML(string=html, base_url=str(md_path.parent)).write_pdf(str(pdf_path))
        print(f"wrote {pdf_path}")


if __name__ == "__main__":
    main()
