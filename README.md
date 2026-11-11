# Портфолио — статический сайт

Многостраничный статический сайт-портфолио продуктового дизайнера: 4 HTML-страницы,
клиентский переключатель языка RU/EN и скрипт-проверка полноты словаря.

## Как открыть

Двойной клик по `index.html` — сайт работает прямо с `file://`.

Никакой сборки, сервера, `fetch()`, ES-модулей и внешних зависимостей. Только HTML,
CSS и ванильный JS. Если открыть через `file://`, всё работает так же, как на хостинге.

## Структура

```
index.html                      # главная: hero, кейсы, обо мне, контакты
cases/youtravel.html            # кейс youtravel.me
cases/finance-dashboard.html    # кейс «Финансовый дашборд»
cases/case-3.html               # кейс-заглушка «Кейс в подготовке»
assets/css/tokens.css           # дизайн-токены (переменные)
assets/css/base.css             # сброс, типографика, сетка
assets/css/components.css       # компоненты
assets/js/i18n.js               # словарь текстов window.I18N (RU/EN)
assets/js/main.js               # применение языка и переключатель
assets/img/…                    # обложки и скриншоты кейсов
scripts/check_i18n.py           # проверка полноты словаря (exit code)
```

## Локализация

- Все видимые тексты размечены атрибутом `data-i18n="ключ"`.
- Тексты лежат в `assets/js/i18n.js` в объекте `window.I18N`:
  `window.I18N[pageId][lang][key]`, где `pageId` — значение `<body data-page="…">`.
- Язык хранится в `localStorage` под ключом `portfolio.lang` (по умолчанию `ru`).
- Кнопка `#langToggle` в шапке переключает язык: в русском режиме показывает `EN`,
  в английском — `RU`. Меняются `<html lang>` и `<html data-lang>`.
- Ключи — плоские, в точечной нотации: `nav.cases`, `hero.title`, `case.yt.title`.

Страницы и их `pageId`:

| Файл | `data-page` |
| --- | --- |
| `index.html` | `index` |
| `cases/youtravel.html` | `case-youtravel` |
| `cases/finance-dashboard.html` | `case-dashboard` |
| `cases/case-3.html` | `case-3` |

## Проверка словаря

```bash
python scripts/check_i18n.py
```

Скрипт вырезает объект после `window.I18N =`, парсит его через `json.loads`,
собирает все ключи `data-i18n` с четырёх страниц и сверяет их с секциями `ru` и `en`.

- `exit 0` — `OK: all data-i18n keys resolved`;
- `exit 1` — список отсутствующих ключей (страница и язык указаны в каждой строке).

Поэтому словарь в `i18n.js` держим в строго JSON-совместимом виде: двойные кавычки,
без trailing comma, без комментариев внутри объекта.

## Что нужно заменить перед публикацией

В HTML стоят явные заглушки с `TODO`-комментариями:

- `https://t.me/USERNAME` → реальный Telegram (в `index.html` и на всех страницах кейсов);
- `mailto:EMAIL@EXAMPLE.COM` → реальный адрес почты;
- галерея кейса youtravel использует `cover.svg` вместо скриншотов экранов;
- `cases/case-3.html` — тексты-заглушки до готовности материалов.

## Заметки по реализации

- `main.js` — IIFE без модулей: `document.querySelectorAll('[data-i18n]')` + `textContent`.
- Тексты без перевода (логотип, `alt` изображений) остаются статичными.
- Если `localStorage` недоступен (приватный режим), выбор языка просто не сохраняется.
- CSS-переменные контракта: `--bg`, `--surface`, `--surface-2`, `--text`, `--muted`,
  `--line`, `--accent`, `--accent-soft`, `--font-sans`, `--fs-hero`, `--fs-h2`, `--fs-h3`,
  `--fs-body`, `--fs-small`, `--space-1…--space-6`, `--radius`, `--radius-pill`,
  `--max`, `--shadow`.
