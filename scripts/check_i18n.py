#!/usr/bin/env python3
"""Проверка полноты словаря переводов.

Парсит assets/js/i18n.js (объект после 'window.I18N ='), затем собирает
все ключи data-i18n с четырёх страниц и сверяет их с ru/en словарями.

Exit code: 0 — всё найдено, 1 — есть пропуски или файл не парсится.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
I18N_JS = ROOT / "assets" / "js" / "i18n.js"

PAGES = [
    ("index", ROOT / "index.html"),
    ("case-youtravel", ROOT / "cases" / "youtravel.html"),
    ("case-dashboard", ROOT / "cases" / "finance-dashboard.html"),
    ("case-3", ROOT / "cases" / "case-3.html"),
]

DATA_I18N_RE = re.compile(r'data-i18n\s*=\s*"([^"]+)"')


def load_dictionary():
    if not I18N_JS.is_file():
        print("FAIL: не найден %s" % I18N_JS)
        sys.exit(1)

    source = I18N_JS.read_text(encoding="utf-8")
    marker = "window.I18N ="
    start = source.find(marker)
    if start == -1:
        print("FAIL: в %s нет присваивания 'window.I18N ='" % I18N_JS.name)
        sys.exit(1)

    raw = source[start + len(marker):].strip()
    if raw.endswith(";"):
        raw = raw[:-1].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print("FAIL: словарь в %s не является валидным JSON: %s" % (I18N_JS.name, exc))
        sys.exit(1)


def collect_keys(html_path):
    text = html_path.read_text(encoding="utf-8")
    seen = []
    for key in DATA_I18N_RE.findall(text):
        if key not in seen:
            seen.append(key)
    return seen


def main():
    dictionary = load_dictionary()
    problems = []
    total_keys = 0

    for page_id, html_path in PAGES:
        rel = html_path.relative_to(ROOT).as_posix()
        if not html_path.is_file():
            problems.append("%s: страница не найдена" % rel)
            continue

        keys = collect_keys(html_path)
        total_keys += len(keys)
        if not keys:
            problems.append("%s: не найдено ни одного data-i18n" % rel)

        page_dict = dictionary.get(page_id)
        if page_dict is None:
            problems.append("%s: в словаре нет страницы '%s'" % (rel, page_id))
            continue

        for lang in ("ru", "en"):
            lang_dict = page_dict.get(lang)
            if not isinstance(lang_dict, dict):
                problems.append("%s: в словаре нет языка '%s'" % (rel, lang))
                continue
            for key in keys:
                if key not in lang_dict:
                    problems.append("%s [%s]: отсутствует ключ '%s'" % (rel, lang, key))

    if problems:
        print("Найдены проблемы (%d):" % len(problems))
        for line in problems:
            print("  - %s" % line)
        sys.exit(1)

    print("OK: all data-i18n keys resolved (%d keys, %d pages)" % (total_keys, len(PAGES)))
    sys.exit(0)


if __name__ == "__main__":
    main()
