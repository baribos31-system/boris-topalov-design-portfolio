#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa_check.py — static QA gate for the portfolio site.

Self-contained: Python standard library only (Python 3.8+), no third-party
dependencies. Run it from anywhere:

    python scripts/qa_check.py
    python scripts/qa_check.py --root /path/to/project

Exit code: 0 when every check passes, 1 when at least one check fails.

Checks
------
(a) required files exist
(b) every relative href/src in every HTML file resolves to an existing file
    (resolved relative to the folder of the page; mailto:, tel:, javascript:,
    data:, http(s):, protocol-relative // and pure fragments are skipped)
(c) every <img> has a non-empty alt attribute
(d) no forbidden JS constructs (fetch( / import / export) — the site has to
    work when opened directly over file://
(e) index.html contains exactly 3 .case-card elements and every link inside
    them resolves

Missing files are reported as a FAIL with a clear message, never as a
traceback: pages that have not been built yet simply fail the gate.

Known limitations of the JS scan
--------------------------------
It is a lightweight lexical scanner, not a JS parser. It blanks out comments,
string literals, template literals and regex literals, then looks for the
forbidden tokens in what is left. Code inside a template-literal ${...}
substitution is not analysed.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REQUIRED_FILES = (
    "index.html",
    "cases/youtravel.html",
    "cases/finance-dashboard.html",
    "cases/case-3.html",
    "assets/css/tokens.css",
    "assets/css/base.css",
    "assets/css/components.css",
    "assets/js/i18n.js",
    "assets/js/main.js",
)

# (d) Constructs that break the site when it is opened over file://.
FORBIDDEN_JS = ("fetch(", "import ", "export ")

# Same class of defect, reported as a warning only (kept out of the gate so the
# required checks stay exactly what was asked for).
WARN_JS = ("import(", "export{")

# Link targets that are not files inside the project.
SKIP_LINK_PREFIXES = (
    "mailto:",
    "tel:",
    "javascript:",
    "data:",
    "http://",
    "https://",
    "//",
)

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# Directories that never contain site pages.
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".qa"}

# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


class PageParser(HTMLParser):
    """Collects link targets, <img> tags and .case-card links of one page."""

    def __init__(self, page: Path):
        super().__init__(convert_charrefs=True)
        self.page = page
        self.links = []        # [(line, attr, value)]
        self.images = []       # [(line, alt_or_None)]
        self.cards = []        # [{"line": int, "links": [(attr, value)]}]
        self._open = []        # stack of currently open tag names
        self._card_stack = []  # stack of open .case-card frames

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _attrs(attrs) -> dict:
        result = {}
        for name, value in attrs:
            if name not in result:  # browsers keep the first occurrence
                result[name] = value
        return result

    # -- HTMLParser API ----------------------------------------------------
    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        data = self._attrs(attrs)

        classes = (data.get("class") or "").split()
        if "case-card" in classes:
            # Depth of the element itself: len(self._open) is measured before
            # the card's own start tag is pushed onto the stack.
            self._card_stack.append({"line": line, "depth": len(self._open), "links": []})

        for attr in ("href", "src"):
            value = data.get(attr)
            if value is None:
                continue
            self.links.append((line, attr, value))
            if self._card_stack:
                self._card_stack[-1]["links"].append((attr, value))

        if tag == "img":
            self.images.append((line, data.get("alt")))

        if tag not in VOID_TAGS:
            self._open.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if tag in self._open:
            while self._open:
                if self._open.pop() == tag:
                    break
        # Close every card whose element has just been popped: the stack is
        # back at the depth the card was opened at.
        while self._card_stack and len(self._open) <= self._card_stack[-1]["depth"]:
            self.cards.append(self._card_stack.pop())

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


# ---------------------------------------------------------------------------
# Link resolution
# ---------------------------------------------------------------------------


def resolve_link(base_dir: Path, root: Path, value: str):
    """Resolve a link target.

    Returns (target_path_or_None, ok, reason).
    """
    raw = value.strip()
    if not raw:
        return None, True, "empty"

    lowered = raw.lower()
    if lowered.startswith(SKIP_LINK_PREFIXES):
        return None, True, "external/scheme"
    if raw.startswith("#"):
        return None, True, "fragment"

    path = raw.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return None, True, "fragment/query only"

    path = unquote(path)
    if path.startswith("/"):
        target = (root / path.lstrip("/")).resolve()
    else:
        target = (base_dir / path).resolve()

    if target.exists():
        return target, True, "ok"
    return target, False, "not found"


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# JS scanning
# ---------------------------------------------------------------------------

REGEX_PRECEDERS = set("(,=:[!&|?{};+-*%~^<>\n")
REGEX_KEYWORDS = {
    "return", "typeof", "instanceof", "in", "of", "new", "delete",
    "void", "throw", "case", "do", "else", "yield", "await",
}


def _regex_starts(text: str, index: int) -> bool:
    """Heuristic: does the '/' at *index* open a regex literal?"""
    j = index - 1
    while j >= 0 and text[j] in " \t\r\n":
        j -= 1
    if j < 0:
        return True
    char = text[j]
    if char.isalnum() or char in "_$":
        k = j
        while k >= 0 and (text[k].isalnum() or text[k] in "_$"):
            k -= 1
        return text[k + 1:j + 1] in REGEX_KEYWORDS
    return char in REGEX_PRECEDERS


def _skip_regex(text: str, index: int):
    """Return the index just past the regex literal starting at *index*."""
    j = index + 1
    n = len(text)
    in_class = False
    while j < n:
        char = text[j]
        if char == "\\":
            j += 2
            continue
        if char == "\n":
            return None  # not a valid regex literal after all
        if in_class:
            if char == "]":
                in_class = False
            j += 1
            continue
        if char == "[":
            in_class = True
            j += 1
            continue
        if char == "/":
            j += 1
            break
        j += 1
    else:
        return None
    while j < n and text[j].isalpha():  # flags
        j += 1
    return j


def mask_js(text: str) -> str:
    """Blank out comments, strings, templates and regexes, keeping positions.

    A forbidden token found in *text* but absent from the masked copy lives in
    a comment or a string literal and is reported as a warning, not a failure.
    """
    out = []
    i = 0
    n = len(text)
    state = "code"  # code | line | block | str | tmpl
    quote = ""
    while i < n:
        char = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if state == "code":
            if char == "/" and nxt == "/":
                out.append("  ")
                i += 2
                state = "line"
                continue
            if char == "/" and nxt == "*":
                out.append("  ")
                i += 2
                state = "block"
                continue
            if char == "/" and _regex_starts(text, i):
                end = _skip_regex(text, i)
                if end is not None:
                    for k in range(i, end):
                        out.append("\n" if text[k] == "\n" else " ")
                    i = end
                    continue
            if char in "\"'":
                quote = char
                out.append(" ")
                i += 1
                state = "str"
                continue
            if char == "`":
                out.append(" ")
                i += 1
                state = "tmpl"
                continue
            out.append(char)
            i += 1
            continue

        if state == "line":
            if char == "\n":
                state = "code"
                out.append("\n")
            else:
                out.append(" ")
            i += 1
            continue

        if state == "block":
            if char == "*" and nxt == "/":
                out.append("  ")
                i += 2
                state = "code"
                continue
            out.append("\n" if char == "\n" else " ")
            i += 1
            continue

        # state == "str" or "tmpl"
        if char == "\\":
            out.append("  " if nxt else " ")
            i += 2
            continue
        if (state == "str" and char == quote) or (state == "tmpl" and char == "`"):
            out.append(" ")
            i += 1
            state = "code"
            continue
        out.append("\n" if char == "\n" else " ")
        i += 1

    return "".join(out)


def scan_js(path: Path, root: Path):
    """Return (problems, warnings) for one JS file."""
    problems = []
    warnings = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"{_rel(path, root)}: cannot read file ({exc})"], warnings

    masked = mask_js(text)
    rel = _rel(path, root)

    for token in FORBIDDEN_JS:
        for match in re.finditer(re.escape(token), text):
            start = match.start()
            if masked[start:start + len(token)] == token:
                line = text.count("\n", 0, start) + 1
                problems.append(
                    f"{rel}:{line}: forbidden construct {token!r} "
                    f"(breaks file://)"
                )

    for token in WARN_JS:
        for match in re.finditer(re.escape(token), text):
            start = match.start()
            if masked[start:start + len(token)] == token:
                line = text.count("\n", 0, start) + 1
                warnings.append(
                    f"{rel}:{line}: {token!r} also breaks file:// "
                    f"(warning only)"
                )

    return problems, warnings


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def _walk_files(root: Path, extensions):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if name.lower().endswith(extensions):
                found.append(Path(dirpath) / name)
    return sorted(found)


def discover_html(root: Path):
    return _walk_files(root, (".html", ".htm"))


def discover_js(root: Path):
    return _walk_files(root, (".js", ".mjs"))


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_required_files(root: Path):
    missing = [rel for rel in REQUIRED_FILES if not (root / rel).is_file()]
    if missing:
        details = [
            f"missing {len(missing)} of {len(REQUIRED_FILES)} required files:"
        ]
        details += [f"  - {rel}" for rel in missing]
        return False, details
    return True, [f"all {len(REQUIRED_FILES)} required files present"]


def check_links(root: Path, pages, parsed):
    if not pages:
        return False, ["no HTML files found under the project root (site not built yet)"]
    problems = []
    total = 0
    for page in pages:
        base_dir = page.parent
        for line, attr, value in parsed[page].links:
            target, ok, _reason = resolve_link(base_dir, root, value)
            if ok:
                total += 1
                continue
            problems.append(
                f"{_rel(page, root)}:{line}: {attr}=\"{value}\" -> not found "
                f"(resolved to {target})"
            )
    if problems:
        return False, problems
    return True, [f"{total} link targets checked in {len(pages)} page(s), all resolve"]


def check_img_alt(root: Path, pages, parsed):
    if not pages:
        return False, ["no HTML files found under the project root (site not built yet)"]
    problems = []
    total = 0
    for page in pages:
        for line, alt in parsed[page].images:
            total += 1
            if alt is None:
                problems.append(f"{_rel(page, root)}:{line}: <img> has no alt attribute")
            elif not alt.strip():
                problems.append(f"{_rel(page, root)}:{line}: <img> has an empty alt attribute")
    if problems:
        return False, problems
    return True, [f"{total} <img> tag(s) checked, all have a non-empty alt"]


def check_js(root: Path, js_files):
    if not js_files:
        return False, ["no JS files found under the project root (site not built yet)"], []
    problems = []
    warnings = []
    for path in js_files:
        file_problems, file_warnings = scan_js(path, root)
        problems += file_problems
        warnings += file_warnings
    if problems:
        return False, problems, warnings
    return True, [f"{len(js_files)} JS file(s) scanned, no forbidden constructs"], warnings


def check_home_cards(root: Path, pages, parsed):
    index = root / "index.html"
    if not index.is_file():
        return False, ["index.html not found in the project root"]

    cards = parsed[index].cards
    problems = []
    if len(cards) != 3:
        problems.append(
            f"index.html: expected exactly 3 .case-card elements, found {len(cards)}"
        )

    for number, card in enumerate(cards, 1):
        if not card["links"]:
            problems.append(
                f"index.html:{card['line']}: .case-card #{number} contains no links"
            )
        for attr, value in card["links"]:
            target, ok, _reason = resolve_link(index.parent, root, value)
            if not ok:
                problems.append(
                    f"index.html:{card['line']}: .case-card #{number} "
                    f"{attr}=\"{value}\" -> not found (resolved to {target})"
                )

    if problems:
        return False, problems
    return True, ["index.html: 3 .case-card elements, all their links resolve"]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class CheckResult:
    def __init__(self, name, passed, details):
        self.name = name
        self.passed = passed
        self.details = details


def run_check(name, func):
    try:
        outcome = func()
    except Exception as exc:  # noqa: BLE001 - a QA gate must never traceback
        return CheckResult(name, False, [f"check crashed: {type(exc).__name__}: {exc}"])
    if isinstance(outcome, tuple) and len(outcome) == 3:
        passed, details, _warnings = outcome
    else:
        passed, details = outcome
    return CheckResult(name, bool(passed), list(details))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Static QA checks for the portfolio site.")
    parser.add_argument("--root", default=str(ROOT), help="project root (default: auto-detect)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: project root does not exist: {root}", file=sys.stderr)
        return 1

    pages = discover_html(root)
    js_files = discover_js(root)
    parsed = {}
    for page in pages:
        try:
            content = page.read_text(encoding="utf-8", errors="replace")
            page_parser = PageParser(page)
            page_parser.feed(content)
            page_parser.close()
            parsed[page] = page_parser
        except Exception as exc:  # noqa: BLE001
            print(f"error: cannot parse {_rel(page, root)}: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            return 1

    print("=" * 72)
    print(" QA CHECK - portfolio static site")
    print(f" root: {root}")
    print(f" pages found: {len(pages)} | js files found: {len(js_files)}")
    print("=" * 72)
    print()

    results = []
    results.append(run_check("(a) required files exist",
                             lambda: check_required_files(root)))
    results.append(run_check("(b) relative links resolve",
                             lambda: check_links(root, pages, parsed)))
    results.append(run_check("(c) <img> alt attributes",
                             lambda: check_img_alt(root, pages, parsed)))
    results.append(run_check("(d) no forbidden JS constructs",
                             lambda: check_js(root, js_files)))
    results.append(run_check("(e) home page case cards",
                             lambda: check_home_cards(root, pages, parsed)))

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}")
        for detail in result.details:
            print(f"       {detail}")
        print()

    warnings = []
    for path in js_files:
        _problems, file_warnings = scan_js(path, root)
        warnings += file_warnings
    if warnings:
        print("WARNINGS (do not fail the gate):")
        for warning in warnings:
            print(f"       {warning}")
        print()

    passed_count = sum(1 for result in results if result.passed)
    failed_count = len(results) - passed_count
    print("-" * 72)
    print(f"RESULT: {'PASS' if failed_count == 0 else 'FAIL'} "
          f"- {passed_count} passed, {failed_count} failed")
    print("-" * 72)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
