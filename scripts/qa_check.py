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
(e) index.html contains exactly 2 .case-card elements and exactly 1
    .request-card with a Telegram link, and every link inside them resolves
(f) every HTML page has data-theme on <html>, a #themeToggle control, a
    .header-cta control and a .hero__title / .case-hero heading block
(g) CSS defines a [data-theme="dark"] block and every token of the contract
    (--accent, --grad-1…--grad-4, --fs-display, --font-display)
(h) every @font-face points at an existing local font file under assets/fonts
    larger than 50 KB
(i) CSS contains no external http(s) references — the site works offline
(j) i18n.js defines keys covering theme, request-card and header-cta

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
import json
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

# (g) Design-token contract that must survive the redesign.
CONTRACT_TOKENS = (
    "--accent",
    "--grad-1",
    "--grad-2",
    "--grad-3",
    "--grad-4",
    "--fs-display",
    "--font-display",
)

# (h) Local webfont requirements.
FONT_DIR_PARTS = ("assets", "fonts")
MIN_FONT_BYTES = 50 * 1024

# (j) i18n keys that must exist for the redesigned components. The patterns are
# deliberately tolerant of separator style: theme.toggle / themeToggle /
# header.theme all count; requestCard.* / request-card.* likewise. The
# "request-card" component may either be keyed as request-card.* or live under
# the shorter request.* namespace — both are accepted.
THEME_KEY_PATTERNS = (
    ("theme", re.compile(r"theme", re.IGNORECASE)),
    ("request-card", re.compile(
        r"(request[._-]?card|(^|\.)request($|[._-]))", re.IGNORECASE
    )),
    ("header-cta", re.compile(r"header[._-]?cta", re.IGNORECASE)),
)

# (e) Home grid contract after the F4 redesign: two case cards plus one NDA
# request card. The request card must expose a Telegram CTA.
EXPECTED_CASE_CARDS = 2
EXPECTED_REQUEST_CARDS = 1

# Classes treated as home-grid cards by the PageParser.
CARD_CLASSES = ("case-card", "request-card")

TELEGRAM_LINK_PREFIXES = (
    "https://t.me/",
    "http://t.me/",
    "https://telegram.me/",
    "http://telegram.me/",
    "tg://resolve?domain=",
)

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
    """Collects link targets, <img> tags and home-card links of one page."""

    def __init__(self, page: Path):
        super().__init__(convert_charrefs=True)
        self.page = page
        self.links = []        # [(line, attr, value)]
        self.images = []       # [(line, alt_or_None)]
        self.cards = []        # .case-card frames: {"class", "line", "links"}
        self.request_cards = []  # .request-card frames, same shape
        self.html_attrs = None  # (line, attrs dict) of the first <html> tag
        self.ids = []          # [(line, id_value, tag)]
        self.classes = []      # [(line, class_name, tag)]
        self._open = []        # stack of currently open tag names
        self._card_stack = []  # stack of open home-card frames (both classes)

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

        if tag == "html" and self.html_attrs is None:
            self.html_attrs = (line, dict(data))
        id_value = data.get("id")
        if id_value:
            self.ids.append((line, str(id_value), tag))

        classes = (data.get("class") or "").split()
        for class_name in classes:
            self.classes.append((line, class_name, tag))
            if class_name in CARD_CLASSES:
                # Depth of the element itself: len(self._open) is measured
                # before the card's own start tag is pushed onto the stack.
                self._card_stack.append({
                    "class": class_name,
                    "line": line,
                    "depth": len(self._open),
                    "links": [],
                })

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
            frame = self._card_stack.pop()
            bucket = self.cards if frame["class"] == "case-card" else self.request_cards
            bucket.append(frame)

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


def discover_css(root: Path):
    return _walk_files(root, (".css",))


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


def is_telegram_href(value: str) -> bool:
    """True when *value* points at a Telegram chat/channel."""
    return value.strip().lower().startswith(TELEGRAM_LINK_PREFIXES)


def check_home_cards(root: Path, pages, parsed):
    index = root / "index.html"
    if not index.is_file():
        return False, ["index.html not found in the project root"]

    data = parsed[index]
    case_cards = data.cards
    request_cards = data.request_cards
    problems = []

    if len(case_cards) != EXPECTED_CASE_CARDS:
        problems.append(
            f"index.html: expected exactly {EXPECTED_CASE_CARDS} .case-card elements "
            f"(current home layout: {EXPECTED_CASE_CARDS} case cards + "
            f"{EXPECTED_REQUEST_CARDS} .request-card), found {len(case_cards)}"
        )
    if len(request_cards) != EXPECTED_REQUEST_CARDS:
        problems.append(
            f"index.html: expected exactly {EXPECTED_REQUEST_CARDS} .request-card "
            f"element (the NDA block next to the {EXPECTED_CASE_CARDS} case cards), "
            f"found {len(request_cards)}"
        )

    for number, card in enumerate(case_cards, 1):
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

    for number, card in enumerate(request_cards, 1):
        if not any(is_telegram_href(value) for _attr, value in card["links"]):
            problems.append(
                f"index.html:{card['line']}: .request-card #{number} has no Telegram "
                f'link (expected href starting with "https://t.me/", '
                f'"http://t.me/" or "tg://resolve?domain=")'
            )
        for attr, value in card["links"]:
            target, ok, _reason = resolve_link(index.parent, root, value)
            if not ok:
                problems.append(
                    f"index.html:{card['line']}: .request-card #{number} "
                    f"{attr}=\"{value}\" -> not found (resolved to {target})"
                )

    if problems:
        return False, problems
    return True, [
        f"index.html: {EXPECTED_CASE_CARDS} .case-card + "
        f"{EXPECTED_REQUEST_CARDS} .request-card with a Telegram CTA, "
        f"all links resolve"
    ]


# ---------------------------------------------------------------------------
# Redesign checks (f)-(j)
# ---------------------------------------------------------------------------


def _line_of(text: str, index: int) -> int:
    """1-based line number of *index* inside *text*."""
    return text.count("\n", 0, index) + 1


def strip_css_comments(text: str) -> str:
    """Replace /* ... */ comments with whitespace, preserving offsets/lines."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end == -1:
                end = n - 2
            chunk = text[i:end + 2]
            out.append("".join("\n" if ch == "\n" else " " for ch in chunk))
            i = end + 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def check_theme_markup(root: Path, pages, parsed):
    """(f) Every page exposes the theme switch, header CTA and hero title."""
    if not pages:
        return False, ["no HTML files found under the project root (site not built yet)"]
    problems = []
    theme_values = []
    for page in pages:
        rel = _rel(page, root)
        data = parsed[page]

        if data.html_attrs is None:
            problems.append(f"{rel}: no <html> tag found")
        else:
            line, attrs = data.html_attrs
            value = attrs.get("data-theme")
            if value is None:
                problems.append(f'{rel}:{line}: <html> has no data-theme attribute')
            elif not str(value).strip():
                problems.append(f'{rel}:{line}: <html> data-theme is empty')
            else:
                value = str(value).strip()
                if value not in theme_values:
                    theme_values.append(value)

        toggles = [entry for entry in data.ids
                   if entry[1] == "themeToggle" and entry[2] in ("button", "a")]
        if not toggles:
            problems.append(
                f'{rel}: no <button id="themeToggle"> or <a id="themeToggle"> found'
            )

        ctas = [entry for entry in data.classes
                if entry[1] == "header-cta" and entry[2] in ("button", "a")]
        if not ctas:
            problems.append(
                f'{rel}: no <button class="... header-cta ..."> or '
                f'<a class="... header-cta ..."> found'
            )

        titles = [entry for entry in data.classes
                  if entry[1] in ("hero__title", "case-hero")]
        if not titles:
            problems.append(
                f"{rel}: no element with class hero__title or case-hero found"
            )

    if problems:
        return False, problems
    values = ", ".join(theme_values) if theme_values else "none"
    return True, [
        f"{len(pages)} page(s): data-theme={values} on <html>, #themeToggle, "
        f".header-cta and hero title present"
    ]


DARK_SELECTOR_RE = re.compile(
    r'\[\s*data-theme\s*=\s*["\']?dark["\']?\s*\]', re.IGNORECASE
)


def check_theme_tokens(root: Path, css_files):
    """(g) CSS defines the dark theme block and the full token contract."""
    if not css_files:
        return False, ["no CSS files found under the project root"]
    problems = []
    dark_files = []
    token_files = {name: [] for name in CONTRACT_TOKENS}

    for path in css_files:
        rel = _rel(path, root)
        text = path.read_text(encoding="utf-8", errors="replace")
        if DARK_SELECTOR_RE.search(text):
            dark_files.append(rel)
        for name in CONTRACT_TOKENS:
            if re.search(re.escape(name) + r"\s*:", text):
                token_files[name].append(rel)

    if not dark_files:
        problems.append(
            'no [data-theme="dark"] selector found in any CSS file '
            "(dark theme block missing)"
        )
    missing = [name for name, files in token_files.items() if not files]
    if missing:
        problems.append("contract tokens missing from CSS: " + ", ".join(missing))

    if problems:
        return False, problems
    return True, [
        'dark theme block defined in: ' + ", ".join(dark_files),
        "contract tokens defined: " + ", ".join(
            f"{name} ({token_files[name][0]})" for name in CONTRACT_TOKENS
        ),
    ]


FONT_FACE_RE = re.compile(r"@font-face\s*\{([^{}]*)\}", re.IGNORECASE | re.DOTALL)
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)([^)\"']+)\1\s*\)", re.IGNORECASE)


def check_local_fonts(root: Path, css_files):
    """(h) @font-face uses an existing local font file (>50 KB) from assets/fonts."""
    if not css_files:
        return False, ["no CSS files found under the project root"]
    problems = []
    faces = 0
    ok_fonts = []
    fonts_dir = root.joinpath(*FONT_DIR_PARTS).resolve()

    for path in css_files:
        rel = _rel(path, root)
        text = strip_css_comments(path.read_text(encoding="utf-8", errors="replace"))
        for match in FONT_FACE_RE.finditer(text):
            faces += 1
            body = match.group(1)
            line = _line_of(text, match.start())
            urls = CSS_URL_RE.findall(body)
            if not urls:
                problems.append(f"{rel}:{line}: @font-face has no url() source")
                continue
            for _quote, raw in urls:
                target_url = unquote(raw.strip())
                lowered = target_url.lower()
                if lowered.startswith(("http://", "https://", "//")):
                    problems.append(
                        f"{rel}:{line}: @font-face points to external URL "
                        f"{target_url!r}"
                    )
                    continue
                if lowered.startswith("data:"):
                    problems.append(
                        f"{rel}:{line}: @font-face uses a data: URI instead of "
                        f"a local font file"
                    )
                    continue
                if target_url.startswith("/"):
                    target = (root / target_url.lstrip("/")).resolve()
                else:
                    target = (path.parent / target_url).resolve()
                try:
                    target.relative_to(fonts_dir)
                except ValueError:
                    problems.append(
                        f"{rel}:{line}: font file is not under assets/fonts: "
                        f"{target_url!r}"
                    )
                    continue
                if not target.is_file():
                    try:
                        shown = target.relative_to(root).as_posix()
                    except ValueError:
                        shown = str(target)
                    problems.append(
                        f"{rel}:{line}: font file not found: {shown}"
                    )
                    continue
                size = target.stat().st_size
                if size <= MIN_FONT_BYTES:
                    shown = target.relative_to(root).as_posix()
                    problems.append(
                        f"{rel}:{line}: font file too small: {shown} = {size} bytes "
                        f"(need > {MIN_FONT_BYTES})"
                    )
                    continue
                ok_fonts.append(f"{target.relative_to(root).as_posix()} ({size} bytes)")

    if faces == 0:
        problems.append("no @font-face rule found in CSS")
    if problems:
        return False, problems
    return True, [
        f"{faces} @font-face rule(s) checked; local fonts: " + ", ".join(ok_fonts)
    ]


def check_offline_css(root: Path, css_files):
    """(i) CSS must not reference external domains (offline operation)."""
    if not css_files:
        return False, ["no CSS files found under the project root"]
    problems = []
    checked = 0
    reported = set()

    for path in css_files:
        rel = _rel(path, root)
        text = strip_css_comments(path.read_text(encoding="utf-8", errors="replace"))

        for match in CSS_URL_RE.finditer(text):
            checked += 1
            raw = unquote(match.group(2).strip())
            if raw.lower().startswith(("http://", "https://", "//")):
                key = (rel, _line_of(text, match.start()), raw)
                if key in reported:
                    continue
                reported.add(key)
                problems.append(
                    f"{key[0]}:{key[1]}: external URL in CSS: {raw!r}"
                )

        for match in re.finditer(r"@import\s+([^;]+);", text, re.IGNORECASE):
            statement = match.group(1)
            line = _line_of(text, match.start())
            external = [
                unquote(url.strip())
                for _quote, url in CSS_URL_RE.findall(statement)
                if url.strip().lower().startswith(("http://", "https://", "//"))
            ]
            bare = re.match(r'\s*["\']([^"\']+)["\']', statement)
            if bare and bare.group(1).lower().startswith(("http://", "https://", "//")):
                external.append(bare.group(1))
            for target in external:
                key = (rel, line, target)
                if key in reported:
                    continue
                reported.add(key)
                problems.append(f"{rel}:{line}: external @import: {target!r}")

    if problems:
        return False, problems
    return True, [
        f"{checked} CSS url() reference(s) checked, no external domains found"
    ]


def load_i18n_keys(path: Path):
    """Return every key of window.I18N, or None when the file is unreadable."""
    if not path.is_file():
        return None
    source = path.read_text(encoding="utf-8", errors="replace")
    marker = "window.I18N ="
    start = source.find(marker)
    if start == -1:
        return None
    raw = source[start + len(marker):].strip()
    if raw.endswith(";"):
        raw = raw[:-1].strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    keys = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                keys.append(str(key))
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return keys


def check_i18n_theme_keys(root: Path):
    """(j) i18n.js defines keys for theme / request-card / header-cta."""
    path = root / "assets" / "js" / "i18n.js"
    keys = load_i18n_keys(path)
    if keys is None:
        return False, [f"{_rel(path, root)}: cannot read or parse the dictionary"]

    problems = []
    found = {}
    for label, pattern in THEME_KEY_PATTERNS:
        matches = sorted({key for key in keys if pattern.search(key)})
        if not matches:
            problems.append(
                f"{_rel(path, root)}: no i18n key covering {label!r} "
                f"(pattern {pattern.pattern!r})"
            )
        else:
            found[label] = matches[:5]

    if problems:
        return False, problems
    return True, [
        f"{_rel(path, root)}: " + "; ".join(
            f"{label}: {', '.join(matches)}" for label, matches in found.items()
        )
    ]


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
    css_files = discover_css(root)
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
    print(f" pages found: {len(pages)} | js files found: {len(js_files)} "
          f"| css files found: {len(css_files)}")
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
    results.append(run_check("(f) theme markup on every page",
                             lambda: check_theme_markup(root, pages, parsed)))
    results.append(run_check("(g) dark theme block + token contract in CSS",
                             lambda: check_theme_tokens(root, css_files)))
    results.append(run_check("(h) local @font-face font files",
                             lambda: check_local_fonts(root, css_files)))
    results.append(run_check("(i) no external URLs in CSS (offline)",
                             lambda: check_offline_css(root, css_files)))
    results.append(run_check("(j) i18n keys for new components",
                             lambda: check_i18n_theme_keys(root)))

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
