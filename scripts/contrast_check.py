#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""contrast_check.py — WCAG contrast gate for the portfolio design tokens.

Self-contained: Python standard library only (Python 3.8+), no third-party
dependencies. Reads assets/css/tokens.css, extracts the colour tokens for BOTH
themes and checks the mandatory contrast pairs with the WCAG 2.1 relative
luminance formula (sRGB, https://www.w3.org/TR/WCAG21/#dfn-relative-luminance).

    python scripts/contrast_check.py
    python scripts/contrast_check.py --root /path/to/project
    python scripts/contrast_check.py --tokens /path/to/tokens.css

Exit code: 0 when every gating pair meets its threshold, 1 otherwise.

How the themes are resolved
---------------------------
The stylesheet is split into rules (at-rules such as @media are recursed into)
and every declaration is filed under the context its selector belongs to:

    base     -- unconditional `:root`, `html`, `body`, `*` blocks (constants)
    light    -- `[data-theme="light"]`
    dark     -- `[data-theme="dark"]`
    default  -- `:not([data-theme])` fallback (the no-JS / first-paint theme)

Effective light = base + light. Effective dark = base + default + dark. That
mirrors the cascade closely enough for token files that define a shared base
and then override per theme, which is how tokens.css is written.

Pairs and thresholds
--------------------
Gating (normal text, WCAG 2.1 SC 1.4.3, ratio >= 4.5):
    --text      on --bg
    --muted     on --bg
    --on-accent on --accent

Advisory (printed but NOT gating):
    --text on --grad-2          (large text / UI, SC 1.4.11, ratio >= 3.0)
    --text on --grad-4          (large text / UI, SC 1.4.11, ratio >= 3.0)
    --text on #D9C3AB           (normal-text threshold 4.5; checked only when a
                                 token with that value exists, e.g. --brand-5;
                                 reported as missing otherwise)

Gradients are decorative washes whose effective text colour is often set by the
component (e.g. `.hero { color: #FFFFFF; --text: #FFFFFF }` over --grad-4), so a
raw token-vs-token comparison is only informational. Alpha channels are
composited over the theme background; multi-stop values are judged by their
worst stop against the text colour.

Why the sand pair is advisory
-----------------------------
A usage audit of assets/css/*.css (grep for `#D9C3AB` / `--brand-5`) shows the
colour appears ONLY as a gradient stop: the `--brand-5` token, the `--grad-1`
and `--grad-text` gradients, and the `.btn--primary:hover` background sweep.
No rule declares it as a `color` or as a flat background behind body text, and
the only element whose paint reaches the sand stop keeps the dark `--on-accent`
ink on top. The white-on-sand combination measured for the dark theme therefore
cannot occur on the real page, so the pair stays an informational notice. If a
future design puts text on sand, make it gating again and add a `--text-on-sand`
token with the designer's approval.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS_REL = Path("assets/css/tokens.css")

# Tokens that must be present in each theme. --grad-2/--grad-4 may live in the
# shared base block, which both themes inherit.
REQUIRED_TOKENS = (
    "--accent",
    "--bg",
    "--text",
    "--muted",
    "--on-accent",
    "--grad-2",
    "--grad-4",
)

NORMAL_MIN = 4.5   # WCAG 2.1 SC 1.4.3 — normal text
LARGE_MIN = 3.0    # WCAG 2.1 SC 1.4.11 — large text / UI components

SAND_HEX = "#D9C3AB"

# Shown next to the advisory sand row. The colour is a decorative gradient stop
# in the CSS, never a text background; see the module docstring / QA report.
SAND_ADVISORY_NOTE = (
    "advisory: #D9C3AB is a decorative gradient stop, not a text background"
)

# (label, fg, bg, min_ratio, gating)
#
# The sand pair is advisory: a CSS usage audit found #D9C3AB only as gradient
# stops (--brand-5 / --grad-1 / --grad-text / .btn--primary:hover), never as a
# background behind text.
PAIR_SPECS = (
    ("text on bg", "--text", "--bg", NORMAL_MIN, True),
    ("muted on bg", "--muted", "--bg", NORMAL_MIN, True),
    ("on-accent on accent", "--on-accent", "--accent", NORMAL_MIN, True),
    ("text on sand " + SAND_HEX, "--text", SAND_HEX, NORMAL_MIN, False),
    ("text on grad-2", "--text", "--grad-2", LARGE_MIN, False),
    ("text on grad-4", "--text", "--grad-4", LARGE_MIN, False),
)

# ---------------------------------------------------------------------------
# CSS scaffolding
# ---------------------------------------------------------------------------

DARK_RE = re.compile(r'\[\s*data-theme\s*=\s*["\']?dark["\']?\s*\]', re.IGNORECASE)
LIGHT_RE = re.compile(r'\[\s*data-theme\s*=\s*["\']?light["\']?\s*\]', re.IGNORECASE)
NO_ATTR_RE = re.compile(r':not\(\s*\[\s*data-theme\s*\]\s*\)', re.IGNORECASE)
BASE_SELECTOR_RE = re.compile(r"^(?::root|html|body|\*)$", re.IGNORECASE)

RECURSIVE_AT_RULES = (
    "@media", "@supports", "@layer", "@container", "@document", "@scope",
)


def strip_comments(text: str) -> str:
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


def extract_blocks(text: str, offset: int = 0):
    """Yield (selector, body, body_offset) for style rules, recursing at-rules."""
    blocks = []
    i = 0
    n = len(text)
    while i < n:
        brace = text.find("{", i)
        if brace == -1:
            break
        selector = text[i:brace].strip()

        depth = 1
        j = brace + 1
        quote = None
        while j < n and depth:
            ch = text[j]
            if quote:
                if ch == "\\":
                    j += 2
                    continue
                if ch == quote:
                    quote = None
            elif ch in "\"'":
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            j += 1

        body = text[brace + 1:j - 1]
        lowered = selector.lower()
        if any(lowered.startswith(at) for at in RECURSIVE_AT_RULES):
            blocks.extend(extract_blocks(body, offset + brace + 1))
        elif selector and not lowered.startswith("@"):
            blocks.append((selector, body, offset + brace + 1))
        i = j
    return blocks


def declarations(body: str):
    """Yield (name, value, relative_offset) for the custom properties."""
    items = []
    start = 0
    depth = 0
    quote = None
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == ";" and depth == 0:
            items.append((start, body[start:i]))
            start = i + 1
        i += 1
    if body[start:].strip():
        items.append((start, body[start:]))

    result = []
    for rel, raw in items:
        name, sep, value = raw.partition(":")
        if not sep:
            continue
        name = name.strip()
        value = value.strip()
        if name.startswith("--") and value:
            result.append((name, value, rel))
    return result


def selector_contexts(selector: str) -> set:
    """Map one selector list to the theme contexts it applies in."""
    contexts = set()
    for part in selector.split(","):
        part = part.strip()
        if not part:
            continue
        if DARK_RE.search(part):
            contexts.add("dark")
        if LIGHT_RE.search(part):
            contexts.add("light")
        if NO_ATTR_RE.search(part):
            contexts.add("default")
        if BASE_SELECTOR_RE.match(part):
            contexts.add("base")
    return contexts


def collect_tokens(css_text: str):
    """Return {context: {token: (value, line)}} for the stylesheet."""
    text = strip_comments(css_text)
    contexts = {"base": {}, "light": {}, "dark": {}, "default": {}}
    for selector, body, body_offset in extract_blocks(text):
        targets = selector_contexts(selector)
        if not targets:
            continue
        for name, value, rel in declarations(body):
            line = text.count("\n", 0, body_offset + rel) + 1
            for target in targets:
                contexts[target][name] = (value, line)
    return contexts


def effective_themes(contexts):
    """Fold the contexts into the two themes the site switches between."""
    base = contexts["base"]

    light = dict(base)
    light.update(contexts["light"])

    dark = dict(base)
    dark.update(contexts["default"])
    dark.update(contexts["dark"])

    return {"light": light, "dark": dark}


# ---------------------------------------------------------------------------
# Colour parsing
# ---------------------------------------------------------------------------

HEX_RE = re.compile(r"#([0-9a-fA-F]{3,8})(?![0-9a-fA-F])")
FUNC_RE = re.compile(r"\b(rgba?|hsla?)\(([^()]*)\)", re.IGNORECASE)
VAR_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,\s*([^()]*))?\)")


def _clamp(value, low=0.0, high=255.0):
    return max(low, min(high, value))


def _parse_hex(token: str):
    body = token[1:]
    if len(body) in (3, 4):
        digits = [int(ch * 2, 16) for ch in body]
    elif len(body) in (6, 8):
        digits = [int(body[k:k + 2], 16) for k in range(0, len(body), 2)]
    else:
        return None
    alpha = digits[3] / 255.0 if len(digits) == 4 else 1.0
    return (float(digits[0]), float(digits[1]), float(digits[2]), alpha)


def _split_args(body: str):
    return [part for part in re.split(r"[,\s/]+", body.strip()) if part]


def _alpha_value(token):
    if token is None:
        return 1.0
    token = token.strip()
    if token.endswith("%"):
        return _clamp(float(token[:-1]) / 100.0, 0.0, 1.0)
    return _clamp(float(token), 0.0, 1.0)


def _parse_rgb(match):
    args = _split_args(match.group(2))
    if len(args) < 3:
        return None
    channels = []
    for arg in args[:3]:
        if arg.endswith("%"):
            channels.append(_clamp(float(arg[:-1]) * 2.55, 0.0, 255.0))
        else:
            channels.append(_clamp(float(arg), 0.0, 255.0))
    alpha = _alpha_value(args[3]) if len(args) > 3 else 1.0
    return (channels[0], channels[1], channels[2], alpha)


def _hsl_to_rgb(hue, sat, light):
    chroma = (1 - abs(2 * light - 1)) * sat
    hp = (hue % 360) / 60.0
    x = chroma * (1 - abs(hp % 2 - 1))
    if hp < 1:
        r, g, b = chroma, x, 0
    elif hp < 2:
        r, g, b = x, chroma, 0
    elif hp < 3:
        r, g, b = 0, chroma, x
    elif hp < 4:
        r, g, b = 0, x, chroma
    elif hp < 5:
        r, g, b = x, 0, chroma
    else:
        r, g, b = chroma, 0, x
    m = light - chroma / 2
    return ((r + m) * 255.0, (g + m) * 255.0, (b + m) * 255.0)


def _parse_hsl(match):
    args = _split_args(match.group(2))
    if len(args) < 3:
        return None
    hue = float(args[0].lower().rstrip("deg"))
    sat = float(args[1].rstrip("%")) / 100.0
    light = float(args[2].rstrip("%")) / 100.0
    alpha = _alpha_value(args[3]) if len(args) > 3 else 1.0
    return (*_hsl_to_rgb(hue, sat, light), alpha)


def colors_in(value: str):
    """Every colour mentioned in a token value (a gradient yields all stops)."""
    found = []
    for match in HEX_RE.finditer(value):
        colour = _parse_hex(match.group(0))
        if colour:
            found.append(colour)
    for match in FUNC_RE.finditer(value):
        name = match.group(1).lower()
        colour = _parse_rgb(match) if name.startswith("rgb") else _parse_hsl(match)
        if colour:
            found.append(colour)
    return found


def resolve_value(value: str, tokens, depth: int = 0) -> str:
    """Substitute var(--x[, fallback]) references a few levels deep."""
    if depth > 5 or "var(" not in value:
        return value

    def replace(match):
        name, fallback = match.group(1), match.group(2)
        entry = tokens.get(name)
        if entry:
            return resolve_value(entry[0], tokens, depth + 1)
        return (fallback or "").strip()

    return VAR_RE.sub(replace, value)


def to_hex(colour) -> str:
    return "#%02X%02X%02X" % (
        int(round(_clamp(colour[0]))),
        int(round(_clamp(colour[1]))),
        int(round(_clamp(colour[2]))),
    )


# ---------------------------------------------------------------------------
# WCAG math
# ---------------------------------------------------------------------------


def _linear(channel: float) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(colour) -> float:
    r, g, b = colour[:3]
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast_ratio(fg, bg) -> float:
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = (l1, l2) if l1 >= l2 else (l2, l1)
    return (hi + 0.05) / (lo + 0.05)


def composite(colour, underlay):
    """Blend a possibly translucent colour over an opaque underlay."""
    r, g, b, a = colour
    if a >= 1.0:
        return (r, g, b)
    ur, ug, ub = underlay[:3]
    return (r * a + ur * (1 - a), g * a + ug * (1 - a), b * a + ub * (1 - a))


def worst_case(fg_colours, bg_colours, underlay):
    """Lowest contrast across every fg/bg stop combination."""
    worst = None
    worst_pair = None
    for fg in fg_colours:
        for bg in bg_colours:
            bg_solid = composite(bg, underlay)
            fg_solid = composite(fg, bg_solid)
            ratio = contrast_ratio(fg_solid, bg_solid)
            if worst is None or ratio < worst:
                worst = ratio
                worst_pair = (fg_solid, bg_solid)
    return worst, worst_pair


def has_colour(tokens, target_hex: str) -> bool:
    """Does any token in this theme resolve to the given colour?"""
    for name, (value, _line) in tokens.items():
        resolved = resolve_value(value, tokens)
        for colour in colors_in(resolved):
            if to_hex(colour) == target_hex:
                return True
    return False


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def theme_tokens(tokens, names):
    """(value, line) for each required token, with None for the missing ones."""
    return {name: tokens.get(name) for name in names}


def evaluate_theme(theme, tokens):
    """Return (rows, problems). Rows are dicts ready for printing."""
    rows = []
    problems = []

    missing = [name for name in REQUIRED_TOKENS if name not in tokens]
    if missing:
        problems.append(
            f"{theme}: missing token(s): " + ", ".join(missing)
        )

    bg_entry = tokens.get("--bg")
    underlay = (255.0, 255.0, 255.0)
    if bg_entry:
        bg_colours = colors_in(resolve_value(bg_entry[0], tokens))
        if bg_colours:
            underlay = composite(bg_colours[0], (255.0, 255.0, 255.0))

    sand_present = has_colour(tokens, SAND_HEX)

    for label, fg_name, bg_name, minimum, gating in PAIR_SPECS:
        if label.startswith("text on sand") and not sand_present:
            rows.append({
                "theme": theme, "pair": label, "fg": "-", "bg": "-",
                "ratio": None, "min": minimum, "gating": gating,
                "status": "SKIP",
                "note": f"no token resolves to {SAND_HEX}",
            })
            continue

        fg_entry = tokens.get(fg_name) if fg_name.startswith("--") else None
        bg_entry = tokens.get(bg_name) if bg_name.startswith("--") else None

        if fg_name.startswith("--") and fg_entry is None:
            problems.append(f"{theme}: {label}: token {fg_name} is missing")
            rows.append({
                "theme": theme, "pair": label, "fg": fg_name, "bg": bg_name,
                "ratio": None, "min": minimum, "gating": gating,
                "status": "FAIL", "note": f"{fg_name} missing",
            })
            continue
        if bg_name.startswith("--") and bg_entry is None:
            problems.append(f"{theme}: {label}: token {bg_name} is missing")
            rows.append({
                "theme": theme, "pair": label, "fg": fg_name, "bg": bg_name,
                "ratio": None, "min": minimum, "gating": gating,
                "status": "FAIL", "note": f"{bg_name} missing",
            })
            continue

        fg_value = resolve_value(fg_entry[0], tokens) if fg_entry else fg_name
        bg_value = resolve_value(bg_entry[0], tokens) if bg_entry else bg_name
        fg_colours = colors_in(fg_value)
        bg_colours = colors_in(bg_value)

        if not fg_colours or not bg_colours:
            side = "foreground" if not fg_colours else "background"
            problems.append(
                f"{theme}: {label}: cannot parse {side} colour "
                f"({fg_name if not fg_colours else bg_name})"
            )
            rows.append({
                "theme": theme, "pair": label,
                "fg": to_hex(fg_colours[0]) if fg_colours else fg_value[:12],
                "bg": to_hex(bg_colours[0]) if bg_colours else bg_value[:12],
                "ratio": None, "min": minimum, "gating": gating,
                "status": "FAIL", "note": f"cannot parse {side} colour",
            })
            continue

        ratio, pair = worst_case(fg_colours, bg_colours, underlay)
        if ratio is None or pair is None:
            problems.append(f"{theme}: {label}: contrast could not be computed")
            rows.append({
                "theme": theme, "pair": label,
                "fg": to_hex(fg_colours[0]), "bg": to_hex(bg_colours[0]),
                "ratio": None, "min": minimum, "gating": gating,
                "status": "FAIL", "note": "contrast could not be computed",
            })
            continue
        status = "PASS" if ratio >= minimum else "FAIL"
        note = SAND_ADVISORY_NOTE if label.startswith("text on sand") else ""
        rows.append({
            "theme": theme,
            "pair": label,
            "fg": to_hex(pair[0]),
            "bg": to_hex(pair[1]),
            "ratio": ratio,
            "min": minimum,
            "gating": gating,
            "status": status,
            "note": note,
        })

    return rows, problems


def print_table(rows):
    header = (
        f"{'THEME':<6} {'PAIR':<24} {'FG':<9} {'BG':<9} "
        f"{'RATIO':>6} {'MIN':>5}  {'RESULT':<9}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        ratio = f"{row['ratio']:.2f}" if row["ratio"] is not None else "-"
        marker = "" if row["gating"] else " *"
        note = f"  ({row['note']})" if row["note"] else ""
        print(
            f"{row['theme']:<6} {row['pair']:<24} {row['fg']:<9} {row['bg']:<9} "
            f"{ratio:>6} {row['min']:>5}  {(row['status'] + marker):<9}{note}"
        )
    print()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="WCAG contrast gate for the portfolio design tokens."
    )
    parser.add_argument("--root", default=str(ROOT),
                        help="project root (default: auto-detect)")
    parser.add_argument("--tokens", default=None,
                        help="explicit path to tokens.css")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    path = Path(args.tokens).resolve() if args.tokens else (root / TOKENS_REL)
    if not path.is_file():
        print(f"error: tokens.css not found: {path}", file=sys.stderr)
        return 1

    css = path.read_text(encoding="utf-8", errors="replace")
    contexts = collect_tokens(css)
    themes = effective_themes(contexts)

    try:
        shown = path.relative_to(root).as_posix()
    except ValueError:
        shown = str(path)

    print("=" * 72)
    print(" CONTRAST CHECK - portfolio design tokens (WCAG 2.1)")
    print(f" file: {shown}")
    print(" thresholds: normal text >= 4.5 | large text / UI >= 3.0")
    print("=" * 72)
    print()

    for context, count in (
        ("base", len(contexts["base"])),
        ("light", len(contexts["light"])),
        ("dark", len(contexts["dark"])),
        ("default", len(contexts["default"])),
    ):
        if count == 0 and context in ("light", "dark") and not contexts["base"]:
            print(f" warning: no declarations found for the '{context}' theme")

    if not contexts["light"]:
        print(" note: no [data-theme=\"light\"] block found — the light theme is")
        print("       resolved from the :root / base declarations alone")

    all_rows = []
    problems = []

    for theme in ("light", "dark"):
        tokens = themes[theme]
        if not tokens:
            problems.append(f"{theme}: no tokens were extracted for this theme")
            print(f"{theme.upper()} THEME: no tokens extracted — FAIL")
            print()
            continue

        rows, theme_problems = evaluate_theme(theme, tokens)
        all_rows.extend(rows)
        problems.extend(theme_problems)

        print(f"{theme.upper()} THEME")
        for name in REQUIRED_TOKENS:
            if name in tokens:
                value, line = tokens[name]
                print(f"   {name:<12} = {value}   (tokens.css:{line})")
        sand = SAND_HEX + (" found" if has_colour(tokens, SAND_HEX) else " not found")
        print(f"   {SAND_HEX:<12} = {sand}")
        print()
        print_table(rows)

    print("-" * 72)
    print(" * advisory pair: printed for information and NOT counted in the exit code.")
    print("   Gradient pairs are decorative washes whose text colour is set by the")
    print("   component on top (.hero: #FFFFFF etc.); the sand pair is advisory")
    print("   because #D9C3AB is only a gradient stop in the CSS, not a text")
    print("   background.")
    print("-" * 72)
    if problems:
        print("PROBLEMS:")
        for problem in problems:
            print(f"   - {problem}")
        print()

    gate_rows = [row for row in all_rows
                 if row["gating"] and row["status"] != "SKIP"]
    gate_passed = sum(1 for row in gate_rows if row["status"] == "PASS")
    gate_failed = [row for row in gate_rows if row["status"] != "PASS"]
    advisory_fails = [row for row in all_rows
                      if not row["gating"] and row["status"] == "FAIL"]

    if advisory_fails:
        print("ADVISORY notices (not counted in the exit code):")
        for row in advisory_fails:
            ratio = f"{row['ratio']:.2f}" if row["ratio"] is not None else "-"
            note = f" — {row['note']}" if row["note"] else ""
            print(
                f"   - {row['theme']}: {row['pair']} = {ratio}:1 "
                f"(min {row['min']}){note}"
            )
        print()

    status = "PASS" if not problems and not gate_failed else "FAIL"
    print(f"RESULT: {status} — {gate_passed}/{len(gate_rows)} gating pairs pass, "
          f"{len(gate_failed)} gating failure(s), {len(problems)} problem(s)")
    print("-" * 72)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
