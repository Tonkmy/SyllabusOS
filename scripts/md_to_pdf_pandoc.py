#!/usr/bin/env python3
"""
Convert Markdown workspace notes to PDFs with Pandoc/XeLaTeX math support.

Examples:
    uv run python scripts/md_to_pdf_pandoc.py "subjects/CSCI/ARIN5204 Reinforcement Learning"
    uv run python scripts/md_to_pdf_pandoc.py "subjects/CSCI/ARIN5204 Reinforcement Learning" --dir detailed
    uv run python scripts/md_to_pdf_pandoc.py "subjects/CSCI/ARIN5204 Reinforcement Learning" --dir detailed --files lec3.3_advanced_policy_gradient.md
    uv run python scripts/md_to_pdf_pandoc.py "subjects/CSCI/ARIN5204 Reinforcement Learning" --backend html
"""

from __future__ import annotations

import argparse
import base64
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path

import markdown
import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["mathtext.fontset"] = "cm"
import matplotlib.pyplot as plt

try:
    from latex2mathml.converter import convert as convert_latex_to_mathml
except Exception:
    convert_latex_to_mathml = None


if sys.platform == "darwin":
    brew_lib = "/opt/homebrew/lib"
    current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if brew_lib not in current:
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = f"{brew_lib}:{current}" if current else brew_lib


PLACEHOLDER = "\x00MATH"
LATEX_TOP_LEVEL_DISPLAY_ENVS = {"equation", "equation*", "align", "align*", "gather", "gather*", "multline", "multline*"}
LATEX_IMAGE_CACHE: dict[tuple[str, bool], str] = {}
PROTECTED_MARKDOWN_RE = re.compile(
    r"(^[ \t]*(```|~~~).*?^[ \t]*\2[ \t]*$|`[^`\n]+`)",
    re.DOTALL | re.MULTILINE,
)
MATH_ENV_RE = re.compile(
    r"\\begin\{(?P<env>equation\*?|align\*?|aligned|gather\*?|multline\*?|split)\}"
    r".*?"
    r"\\end\{(?P=env)\}",
    re.DOTALL,
)


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
    font-family: "Helvetica Neue", Helvetica, Arial, "Hiragino Sans GB", "Heiti SC", "Songti SC", "Arial Unicode MS", sans-serif;
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

.math-latex-image {{
    height: auto;
    vertical-align: middle;
}}

math {{
    font-family: "STIX Two Math", "Latin Modern Math", "Cambria Math", "Times New Roman", serif;
}}

.math-display math {{
    font-size: 1.05em;
}}

.math-inline math {{
    font-size: 1em;
}}

.math-fallback {{
    color: #8a1f11;
    white-space: pre-wrap;
}}
"""


def latex_to_svg(latex: str, display: bool) -> str:
    fontsize = 14 if display else 11
    fig = None
    try:
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
        buf.seek(0)
        payload = base64.b64encode(buf.read()).decode("utf-8")
        if display:
            return f'<div class="math-display"><img src="data:image/svg+xml;base64,{payload}"/></div>'
        return f'<img class="math-inline" src="data:image/svg+xml;base64,{payload}"/>'
    finally:
        if fig is not None:
            plt.close(fig)


def latex_document_body(latex: str, display: bool) -> str:
    stripped = latex.strip()
    env_match = re.match(r"\\begin\{([^}]+)\}", stripped)
    if display and env_match and env_match.group(1) in LATEX_TOP_LEVEL_DISPLAY_ENVS:
        return stripped
    if display:
        return f"\\[\n{stripped}\n\\]"
    return f"\\({stripped}\\)"


def summarize_latex_output(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return "no output"
    return " | ".join(lines[-5:])


def latex_to_png(latex: str, display: bool) -> str | None:
    cache_key = (latex, display)
    if cache_key in LATEX_IMAGE_CACHE:
        return LATEX_IMAGE_CACHE[cache_key]

    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        return None

    font_command = r"\large" if display else r"\normalsize"
    document = rf"""
\documentclass[12pt]{{article}}
\usepackage[paperwidth=14in,paperheight=7in,margin=0.2in]{{geometry}}
\usepackage[utf8]{{inputenc}}
\usepackage{{amsmath,amssymb}}
\pagestyle{{empty}}
\begin{{document}}
\centering
{font_command}
{latex_document_body(latex, display)}
\end{{document}}
"""
    with tempfile.TemporaryDirectory(prefix="md_to_pdf_math_") as tmp:
        tmp_dir = Path(tmp)
        tex_path = tmp_dir / "math.tex"
        tex_path.write_text(document, encoding="utf-8")
        try:
            result = subprocess.run(
                [pdflatex, "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
                cwd=tmp_dir,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=20,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("pdflatex timed out") from exc
        if result.returncode != 0:
            raise RuntimeError(summarize_latex_output(result.stdout))

        import fitz
        from PIL import Image, ImageChops

        pdf_path = tmp_dir / "math.pdf"
        doc = fitz.open(pdf_path)
        zoom = 3.0
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        image = Image.open(BytesIO(pix.tobytes("png"))).convert("RGBA")
        rgb_image = image.convert("RGB")
        background = Image.new("RGB", image.size, (255, 255, 255))
        bbox = ImageChops.difference(rgb_image, background).getbbox()
        if bbox is None:
            raise RuntimeError("pdflatex produced a blank formula")

        padding = 8
        left = max(bbox[0] - padding, 0)
        upper = max(bbox[1] - padding, 0)
        right = min(bbox[2] + padding, image.width)
        lower = min(bbox[3] + padding, image.height)
        image = image.crop((left, upper, right, lower))

        transparent_pixels = []
        for red, green, blue, alpha in image.getdata():
            if red > 250 and green > 250 and blue > 250:
                transparent_pixels.append((255, 255, 255, 0))
            else:
                transparent_pixels.append((red, green, blue, alpha))
        image.putdata(transparent_pixels)

        buf = BytesIO()
        image.save(buf, format="PNG")
        payload = base64.b64encode(buf.getvalue()).decode("utf-8")
        css_width = image.width / zoom * 96 / 72
        style = f"width: {css_width:.1f}px; max-width: 100%;"
        image_html = f'<img class="math-latex-image" style="{style}" src="data:image/png;base64,{payload}"/>'
        if display:
            result_html = f'<div class="math-display">{image_html}</div>'
        else:
            result_html = image_html
        LATEX_IMAGE_CACHE[cache_key] = result_html
        return result_html


def latex_to_mathml(latex: str, display: bool) -> str | None:
    if convert_latex_to_mathml is None:
        return None

    display_value = "block" if display else "inline"
    try:
        mathml = convert_latex_to_mathml(latex, display=display_value)
    except TypeError:
        mathml = convert_latex_to_mathml(latex)

    mathml = re.sub(
        r'(<math\b[^>]*?)\sdisplay="[^"]*"',
        rf'\1 display="{display_value}"',
        mathml,
        count=1,
    )
    mathml = re.sub(
        r"(<math\b[^>]*?)\sdisplay='[^']*'",
        rf'\1 display="{display_value}"',
        mathml,
        count=1,
    )
    opening_tag = mathml.split(">", 1)[0]
    if "display=" not in opening_tag:
        mathml = mathml.replace("<math", f'<math display="{display_value}"', 1)
    return mathml


def shorten_latex(latex: str, limit: int = 110) -> str:
    compact = " ".join(latex.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def fallback_math(latex: str, display: bool) -> str:
    delim = "$$" if display else "$"
    escaped = html.escape(f"{delim}{latex}{delim}")
    if display:
        return f'<div class="math-display"><code class="math-fallback">{escaped}</code></div>'
    return f'<code class="math-inline math-fallback">{escaped}</code>'


def latex_to_html(latex: str, display: bool, math_warnings: list[str]) -> str:
    try:
        return latex_to_svg(latex, display)
    except Exception as exc:
        svg_error = exc

    try:
        latex_png = latex_to_png(latex, display)
        if latex_png:
            return latex_png
    except Exception as exc:
        latex_png_error = exc
    else:
        latex_png_error = "pdflatex is not available"

    try:
        mathml = latex_to_mathml(latex, display)
        if mathml:
            if display:
                return f'<div class="math-display">{mathml}</div>'
            return f'<span class="math-inline">{mathml}</span>'
    except Exception as exc:
        math_warnings.append(f"SVG failed: {shorten_latex(latex)} ({svg_error})")
        math_warnings.append(f"LaTeX image fallback failed: {shorten_latex(latex)} ({latex_png_error})")
        math_warnings.append(f"MathML fallback failed: {shorten_latex(latex)} ({exc})")
        return fallback_math(latex, display)

    math_warnings.append(f"SVG failed: {shorten_latex(latex)} ({svg_error})")
    math_warnings.append(f"LaTeX image fallback failed: {shorten_latex(latex)} ({latex_png_error})")
    math_warnings.append(f"latex2mathml is unavailable for: {shorten_latex(latex)}")
    return fallback_math(latex, display)


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    pos = index - 1
    while pos >= 0 and text[pos] == "\\":
        backslashes += 1
        pos -= 1
    return backslashes % 2 == 1


def find_unescaped(text: str, needle: str, start: int) -> int:
    pos = start
    while True:
        pos = text.find(needle, pos)
        if pos == -1:
            return -1
        if not is_escaped(text, pos):
            return pos
        pos += len(needle)


def is_single_dollar(text: str, index: int) -> bool:
    if text[index] != "$" or is_escaped(text, index):
        return False
    prev_is_dollar = index > 0 and text[index - 1] == "$"
    next_is_dollar = index + 1 < len(text) and text[index + 1] == "$"
    return not prev_is_dollar and not next_is_dollar


def find_single_dollar(text: str, start: int) -> int:
    pos = start
    while True:
        pos = text.find("$", pos)
        if pos == -1:
            return -1
        if is_single_dollar(text, pos):
            return pos
        pos += 1


def find_next_math_start(text: str, start: int) -> tuple[int, str] | None:
    candidates: list[tuple[int, str]] = []

    for delimiter, kind in (("$$", "display_dollar"), (r"\[", "display_bracket"), (r"\(", "inline_bracket")):
        pos = find_unescaped(text, delimiter, start)
        if pos != -1:
            candidates.append((pos, kind))

    dollar_pos = find_single_dollar(text, start)
    if dollar_pos != -1:
        candidates.append((dollar_pos, "inline_dollar"))

    env_match = MATH_ENV_RE.search(text, start)
    if env_match:
        candidates.append((env_match.start(), "environment"))

    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])


def convert_math_segment(text: str, fragments: list[str], math_warnings: list[str]) -> str:
    parts: list[str] = []
    pos = 0

    def stash(latex: str, display: bool) -> str:
        index = len(fragments)
        fragments.append(latex_to_html(latex.strip(), display, math_warnings))
        return f"{PLACEHOLDER}{index}\x00"

    while pos < len(text):
        start = find_next_math_start(text, pos)
        if start is None:
            parts.append(text[pos:])
            break

        start_pos, kind = start
        parts.append(text[pos:start_pos])

        if kind == "display_dollar":
            end_pos = find_unescaped(text, "$$", start_pos + 2)
            if end_pos == -1:
                parts.append(text[start_pos:])
                break
            parts.append(stash(text[start_pos + 2 : end_pos], display=True))
            pos = end_pos + 2
        elif kind == "display_bracket":
            end_pos = find_unescaped(text, r"\]", start_pos + 2)
            if end_pos == -1:
                parts.append(text[start_pos:])
                break
            parts.append(stash(text[start_pos + 2 : end_pos], display=True))
            pos = end_pos + 2
        elif kind == "inline_bracket":
            end_pos = find_unescaped(text, r"\)", start_pos + 2)
            if end_pos == -1:
                parts.append(text[start_pos:])
                break
            parts.append(stash(text[start_pos + 2 : end_pos], display=False))
            pos = end_pos + 2
        elif kind == "inline_dollar":
            end_pos = find_single_dollar(text, start_pos + 1)
            if end_pos == -1:
                parts.append(text[start_pos:])
                break
            parts.append(stash(text[start_pos + 1 : end_pos], display=False))
            pos = end_pos + 1
        else:
            env_match = MATH_ENV_RE.match(text, start_pos)
            if env_match is None:
                parts.append(text[start_pos])
                pos = start_pos + 1
                continue
            parts.append(stash(env_match.group(0), display=True))
            pos = env_match.end()

    return "".join(parts)


def convert_math(md_text: str, math_warnings: list[str]) -> tuple[str, list[str]]:
    fragments: list[str] = []
    parts: list[str] = []
    pos = 0

    for protected_match in PROTECTED_MARKDOWN_RE.finditer(md_text):
        converted = convert_math_segment(
            md_text[pos : protected_match.start()],
            fragments,
            math_warnings,
        )
        parts.append(converted)
        parts.append(protected_match.group(0))
        pos = protected_match.end()

    converted = convert_math_segment(
        md_text[pos:],
        fragments,
        math_warnings,
    )
    parts.append(converted)
    return "".join(parts), fragments


def restore_math(html: str, fragments: list[str]) -> str:
    return re.sub(rf"{PLACEHOLDER}(\d+)\x00", lambda match: fragments[int(match.group(1))], html)


def md_to_html(md_text: str, course_name: str, math_warnings: list[str] | None = None) -> str:
    if math_warnings is None:
        math_warnings = []
    md_text, fragments = convert_math(md_text, math_warnings)
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


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def build_pandoc_header(course_name: str) -> str:
    escaped_course = latex_escape(course_name)
    return rf"""
\usepackage{{amsmath,amssymb,mathtools,bm}}
\usepackage{{booktabs,longtable,array}}
\usepackage{{xcolor}}
\usepackage{{fancyhdr}}

\pagestyle{{fancy}}
\fancyhf{{}}
\rhead{{\footnotesize {escaped_course}}}
\cfoot{{\footnotesize Page \thepage}}
\setlength{{\headheight}}{{14pt}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{0.45em}}
\allowdisplaybreaks

\renewcommand{{\arraystretch}}{{1.15}}
\AtBeginDocument{{\renewcommand{{\boldsymbol}}[1]{{\symbf{{#1}}}}}}
\newcommand{{\argmax}}{{\operatorname*{{arg\,max}}}}
\newcommand{{\argmin}}{{\operatorname*{{arg\,min}}}}
"""


def find_pandoc() -> str | None:
    system_pandoc = shutil.which("pandoc")
    if system_pandoc:
        return system_pandoc

    try:
        import pypandoc
    except Exception:
        return None

    package_pandoc = Path(pypandoc.__file__).resolve().parent / "files" / "pandoc"
    if package_pandoc.exists() and os.access(package_pandoc, os.X_OK):
        return str(package_pandoc)
    return None


def find_pdf_engine(preferred: str) -> str:
    if preferred != "auto":
        engine = shutil.which(preferred)
        if engine is None:
            raise SystemExit(f"PDF engine not found: {preferred}")
        return engine

    for candidate in ("xelatex", "lualatex", "pdflatex"):
        engine = shutil.which(candidate)
        if engine:
            return engine
    raise SystemExit("no TeX PDF engine found. Install xelatex, lualatex, or pdflatex.")


def pandoc_markdown_format() -> str:
    return (
        "markdown"
        "+tex_math_dollars"
        "+raw_tex"
        "+pipe_tables"
        "+fenced_code_blocks"
        "+backtick_code_blocks"
        "+yaml_metadata_block"
        "+smart"
    )


def summarize_command_output(output: str, limit: int = 5000) -> str:
    output = output.strip()
    if len(output) <= limit:
        return output
    return f"{output[-limit:]}"


def run_pandoc_pdf(md_path: Path, pdf_path: Path, course_dir: Path, course_name: str, pdf_engine: str) -> None:
    pandoc = find_pandoc()
    if pandoc is None:
        raise SystemExit(
            "pandoc is not available. Run `uv sync` to install pypandoc-binary, "
            "or install system pandoc with `brew install pandoc`."
        )

    engine = find_pdf_engine(pdf_engine)
    resource_path = os.pathsep.join([str(md_path.parent), str(course_dir), str(course_dir / "notes")])

    with tempfile.TemporaryDirectory(prefix="md_to_pdf_pandoc_") as tmp:
        header_path = Path(tmp) / "header.tex"
        header_path.write_text(build_pandoc_header(course_name), encoding="utf-8")

        cmd = [
            pandoc,
            str(md_path),
            "--from",
            pandoc_markdown_format(),
            "--standalone",
            "--pdf-engine",
            engine,
            "--include-in-header",
            str(header_path),
            "--resource-path",
            resource_path,
            "--syntax-highlighting",
            "tango",
            "-V",
            "papersize=a4",
            "-V",
            "geometry:margin=2cm",
            "-V",
            "fontsize=11pt",
            "-V",
            "colorlinks=true",
            "-V",
            "linkcolor=blue",
            "-V",
            "urlcolor=blue",
            "-M",
            f"title={md_path.stem.replace('_', ' ')}",
            "-o",
            str(pdf_path),
        ]

        result = subprocess.run(
            cmd,
            cwd=md_path.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"pandoc failed for {md_path.name} with exit code {result.returncode}\n"
                f"{summarize_command_output(result.stdout)}"
            )


def write_html_pdf(md_path: Path, pdf_path: Path, course_name: str) -> list[str]:
    try:
        from weasyprint import HTML
    except Exception as exc:
        raise SystemExit(
            "weasyprint is not available. Run `uv sync` and ensure required system libraries are installed."
        ) from exc

    math_warnings: list[str] = []
    html_text = md_to_html(md_path.read_text(encoding="utf-8"), course_name, math_warnings)
    HTML(string=html_text, base_url=str(md_path.parent)).write_pdf(str(pdf_path))
    return math_warnings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("course_dir", help="path to the workspace directory")
    parser.add_argument(
        "--dir",
        default="chapters",
        help="note subdirectory under notes/ to export (default: chapters)",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="specific markdown files; relative names are resolved under notes/<dir>/ first",
    )
    parser.add_argument(
        "--backend",
        choices=("pandoc", "html"),
        default="pandoc",
        help="PDF conversion backend (default: pandoc)",
    )
    parser.add_argument(
        "--pdf-engine",
        default="auto",
        help="TeX engine for the pandoc backend: auto, xelatex, lualatex, or pdflatex (default: auto)",
    )
    return parser.parse_args()


def resolve_requested_path(course_dir: Path, notes_dir: Path, requested: str) -> Path:
    path = Path(requested).expanduser()
    if path.is_absolute():
        return path

    notes_root = course_dir / "notes"
    candidates = [
        notes_dir / path,
        notes_root / path,
        course_dir / path,
        Path.cwd() / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def resolve_targets(course_dir: Path, notes_subdir: str, requested: list[str] | None) -> list[Path]:
    notes_dir = course_dir / "notes" / notes_subdir
    if requested:
        return [resolve_requested_path(course_dir, notes_dir, name) for name in requested]
    if not notes_dir.is_dir():
        raise SystemExit(f"notes directory not found: {notes_dir}")
    return sorted(notes_dir.glob("*.md"))


def main() -> None:
    args = parse_args()
    course_dir = Path(args.course_dir).resolve()
    if not course_dir.is_dir():
        raise SystemExit(f"workspace directory not found: {course_dir}")

    if args.backend == "html" and convert_latex_to_mathml is None:
        print("note: latex2mathml is not installed; using Matplotlib mathtext fallback for formulas")

    targets = resolve_targets(course_dir, args.dir, args.files)
    if not targets:
        raise SystemExit(f"no markdown files found under {course_dir / 'notes' / args.dir}")

    export_dir = course_dir / "notes" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    for md_path in targets:
        if not md_path.exists():
            print(f"skip: {md_path} not found")
            continue
        pdf_path = export_dir / f"{md_path.stem}.pdf"
        try:
            if args.backend == "pandoc":
                run_pandoc_pdf(md_path, pdf_path, course_dir, course_dir.name, args.pdf_engine)
                print(f"wrote {pdf_path}")
            else:
                math_warnings = write_html_pdf(md_path, pdf_path, course_dir.name)
                print(f"wrote {pdf_path}")
                for warning in math_warnings:
                    print(f"  warning: {md_path.name}: {warning}")
        except Exception as exc:
            raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
