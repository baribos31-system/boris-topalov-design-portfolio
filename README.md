# Портфолио — статический сайт

Многостраничный статический сайт-портфолио продуктового дизайнера: 4 HTML-страницы,
две темы (тёмная по умолчанию / светлая), переключатель языка RU/EN, локальный
вариативный гротеск и скрипт-проверка полноты словаря.

## Как открыть

Двойной клик по `index.html` — сайт работает прямо с `file://`.

Никакой сборки, сервера, `fetch()`, ES-модулей и внешних зависимостей. Только HTML,
CSS, ванильный JS и один локальный файл шрифта. Если открыть через `file://`, всё
работает так же, как на хостинге (проверено в Chromium: тема, язык, шрифт).

## Структура

```
index.html                      # главная: hero, кейсы, обо мне, контакты
cases/youtravel.html            # кейс youtravel.me
cases/finance-dashboard.html    # кейс «Финансовый дашборд»
cases/case-3.html               # страница-заглушка (noindex, ссылок на неё нет)
assets/css/tokens.css           # дизайн-токены: цвет, типографика, тени, две темы
assets/css/base.css             # @font-face, сброс, типографика, сетка, утилиты
assets/css/components.css       # компоненты: шапка, hero, карточки, cta-band…
assets/js/i18n.js               # словарь текстов window.I18N (RU/EN)
assets/js/main.js               # применение языка + переключатель темы
assets/fonts/Manrope-Variable.woff2   # вариативный гротеск, wght 200–800
assets/fonts/OFL.txt            # лицензия шрифта (SIL OFL 1.1)
assets/img/…                    # обложки и скриншоты кейсов, шум и глоу
scripts/check_i18n.py           # проверка полноты словаря (exit code)
scripts/qa_check.py             # структурный QA-гейт (exit code)
```

## Темы

Две темы, переключаются кнопкой `.theme-toggle` (`#themeToggle`) в шапке.

- состояние живёт в атрибуте `<html data-theme="dark|light">`; по умолчанию `dark`;
- выбор хранится в `localStorage['portfolio.theme']`;
- в `tokens.css` темы описаны селекторами `[data-theme="dark"]` и `[data-theme="light"]`,
  поэтому переключение — это смена значений CSS-переменных, без перерисовки разметки;
- тёмные и светлые полосы (hero, `case-block`, `section--light`, `cta-band`) задают
  локальную область токенов: они остаются тёмными/светлыми в обеих темах;
- в `<head>` каждой страницы стоит короткий inline-скрипт, который выставляет
  `data-theme` из `localStorage` до первой отрисовки — иначе при выборе светлой темы
  видна вспышка тёмной;
- `body` меняет `background-color` и `color` с переходом 0.3s; при
  `prefers-reduced-motion: reduce` переходы отключены.

Кнопка темы — иконка (солнце в тёмной теме, луна в светлой), поэтому `main.js`
не перезаписывает её содержимое, а обновляет только локализованный `aria-label`
(`theme.toLight` / `theme.toDark`). Язык и тема независимы: можно смотреть сайт
по-английски в светлой теме.

## Типографика

Заголовки и текст — один вариативный гротеск **Manrope** (wght 200–800, Cyrillic +
Latin, SIL OFL 1.1). Файл лежит в `assets/fonts/Manrope-Variable.woff2` (52.5 КБ),
подключён через `@font-face` в `base.css` с `font-display: swap` и предзагружается
`<link rel="preload" as="font">`. Внешних CDN нет.

Почему не Archivo, как планировалось изначально: в Archivo нет кириллицы, а сайт
двуязычный — русские заголовки отваливались бы в системный шрифт. Имя семейства
в `@font-face` совпадает с первым значением `--font-display` / `--font-sans`
в `tokens.css` (`"Manrope"`), поэтому стек токенов менять не пришлось.

## Локализация

- Все видимые тексты размечены атрибутом `data-i18n="ключ"`.
- Тексты лежат в `assets/js/i18n.js` в объекте `window.I18N`:
  `window.I18N[pageId][lang][key]`, где `pageId` — значение `<body data-page="…">`.
- Язык хранится в `localStorage` под ключом `portfolio.lang` (по умолчанию `ru`).
- Кнопка `#langToggle` в шапке переключает язык: в русском режиме показывает `EN`,
  в английском — `RU`. Меняются `<html lang>` и `<html data-lang>`.
- Ключи — плоские, в точечной нотации: `nav.cases`, `hero.title`, `case.yt.title`.
- Строка доверия в hero собрана из трёх ключей (`hero.meta.years`, `hero.meta.role`,
  `hero.meta.domains`); между ними стоят отдельные элементы `.hero__meta-sep`
  (`aria-hidden="true"`, текст `·`), поэтому при переносе строка не начинается
  с висячего разделителя.

Страницы и их `pageId`:

| Файл | `data-page` |
| --- | --- |
| `index.html` | `index` |
| `cases/youtravel.html` | `case-youtravel` |
| `cases/finance-dashboard.html` | `case-dashboard` |
| `cases/case-3.html` | `case-3` |

## Проверки

```bash
python scripts/check_i18n.py     # словарь: все data-i18n ключи есть в ru и en
python scripts/qa_check.py       # структура: файлы, ссылки, alt, запрещённый JS
```

`check_i18n.py` вырезает объект после `window.I18N =`, парсит его через `json.loads`,
собирает все ключи `data-i18n` с четырёх страниц и сверяет их с секциями `ru` и `en`.
Поэтому словарь держим в строго JSON-совместимом виде: двойные кавычки, без trailing
comma, без комментариев внутри объекта.

> **Известное расхождение:** `scripts/qa_check.py`, проверка (e), всё ещё требует
> «ровно 3 элемента `.case-card`» на главной. После правки F4 карточек две, а третьим
> элементом сетки стал `.request-card` («Приватные кейсы под NDA»). Проверку нужно
> обновить на `2 .case-card + 1 .request-card`; файл принадлежит зоне Engineer.

## Что нужно заменить перед публикацией

В HTML стоят явные заглушки с `TODO`-комментариями:

- `https://t.me/USERNAME` → реальный Telegram (шапка, hero, request-card, все CTA);
- `mailto:EMAIL@EXAMPLE.COM` → реальный адрес почты;
- галерея кейса youtravel использует `cover.svg` вместо скриншотов экранов;
- `cases/case-3.html` — тексты-заглушки до готовности материалов (страница помечена
  `noindex`, ссылок на неё с главной и из навигации нет).

## Заметки по реализации

- `main.js` — IIFE без модулей: `document.querySelectorAll('[data-i18n]')` + `textContent`.
  `fetch`/`import`/`export` отсутствуют, сайт работает по `file://`.
- Тексты без перевода (логотип, `alt` изображений, `aria-label` навигации) остаются
  статичными; `aria-label` кнопок темы и языка локализуется в `main.js`.
- Если `localStorage` недоступен (приватный режим, ограничения `file://`), выбор
  темы и языка просто не сохраняется — сайт работает на значениях по умолчанию.
- CSS-переменные контракта: `--bg`, `--surface`, `--surface-2`, `--text`, `--muted`,
  `--line`, `--accent`, `--accent-strong`, `--accent-soft`, `--accent-ink`,
  `--on-accent`, `--font-display`, `--font-sans`, `--fs-hero`, `--fs-h2`, `--fs-h3`,
  `--fs-body`, `--fs-small`, `--space-1…--space-6`, `--radius`, `--radius-sm`,
  `--radius-pill`, `--max`, `--shadow`, `--grad-1…--grad-4`, `--glow`,
  `--grain-opacity`, `--fs-display`, `--tracking-display`, `--shadow-glow`,
  `--header-h`.
- Правки по отчёту Lazyweb: F1 — заголовок hero описывает специализацию, а не общий
  слоган; F3 — постоянный CTA в шапке (`.header-cta`), без плавающей панели;
  F4 — карточка «Кейс в подготовке» заменена на `.request-card` про кейсы под NDA;
  F5 — опыт и уровень вынесены в `.hero__meta` отдельной строкой.
