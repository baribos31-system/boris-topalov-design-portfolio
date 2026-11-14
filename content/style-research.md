# Стиль-исследование: тёмно-оранжевый портфолио (Boris Topalov)

Палитра: фон #000000; оранж #E85002; градиент #000000 → #C10801 → #F16001 → #D9C3AB;
нейтрали #F9F9F9, #A7A7A7, #646464, #333333; зернистые (grain) градиенты; glow-полусфера.
Темы: тёмная + светлая.

## 1. Шрифты для крупного UPPERCASE-гротеска

Все семьи — OFL-1.1 (бесплатно, локальная укладка без CDN допустима, накладки OFL-1.1 не требуют лицензированной отпечатки в продукте, нужен лишь текст лицензии рядом с шрифтами). Загрузка с официального репозитория google/fonts (raw.githubusercontent.com = официальный источник семейств). Размеры — замерены HEAD-запросом.

### Кандидаты

| Шрифт | Данные | Байт (ttf) | URL скачивания (официальный) |
|---|---|---|---|
| **Archivo** (Omnibus-Type, 2012/2021, OFL-1.1) | grotesque, high contrast, 9 весов (100–900) + ось ширины wdth 62–125, italic, полная установка (латиница + кириллица, контент-пакет gfonts — латиница) | 658 596 | https://raw.githubusercontent.com/google/fonts/main/ofl/archivo/Archivo%5Bwdth%2Cwght%5D.ttf |
| **Archivo Italic** (variable) | тот же скоуп, italic | 741 368 | https://raw.githubusercontent.com/google/fonts/main/ofl/archivo/Archivo-Italic%5Bwdth%2Cwght%5D.ttf |
| **Inter Tight** (Rasmus Andersson, 2022, OFL-1.1) | variable wght 100–900, cyrillic + greek + latin + vietnamese, тёстовый сжатый гротеск, удобен для малого текста | 581 588 | https://raw.githubusercontent.com/google/fonts/main/ofl/intertight/InterTight%5Bwght%5D.ttf |
| **Space Grotesk** (Florian Karsten, 2020, OFL-1.1) | variable wght 300–700, дерзкий гротеск с «моноблоковым» рисунком, но **латиница только** (latin-ext, vietnamese, menu) | 136 676 | https://raw.githubusercontent.com/google/fonts/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf |
| **Anton** (Vernon Adams, 2011, OFL-1.1) | display, штопорная конденсация, высокая контрастность, 1 вес 400, латиница + vietnamese, малый размер | 170 812 | https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf |
| **Bebas Neue** (Dharma Type / Ryoichi Tsunekawa, 2010, OFL-1.1) | display, ультра-конденсация в виде высоких капс, 1 вес 400, латиница | 61 400 | https://raw.githubusercontent.com/google/fonts/main/ofl/bebasneue/BebasNeue-Regular.ttf |

### Примечания по кандидатам

- **Archivo Expanded** — отдельной семьи «Archivo Expanded» в google/fonts нет. Полная ширина = ось `wdth: 125` того же variable-файла, на котором можно подстроить композицию (Archivo в статике так же не выделяется — только variable; Fontsource ссылается на переменный файл). Для «раскрытых» заголовков задаётся `font-stretch: 125%` или `font-variation-settings: 'wdth' 125`.
- **Space Grotesk** — русский текст не покрывается. Для связки «глотоблок → русский» в ней требуется fallback на Inter Tight.
- **Anton** — одна статическая начертание (400), но именно оно читает себя на фоне чёрного как звук-выстрел; вес файла ~171 КБ.
- **Bebas Neue** — строго display; для капса-атрибутики подойдёт как отдельный слой (карточки, метрики).
- **Inter Tight** — единственный из списка с кириллицей; variable, поэтому под любые масштабы.

### Финальная рекомендация

- **Дисплейный (главный, UPPERCASE)**: **Anton** — для «огромного капса» в гротеске идеален: конденсация, 300–900-полный контраст, малый вес. **Альтернатива** — `Archivo` с `font-variation-settings: 'wdth' 125` (редакторский, широкий, изящный).
- **Текстовый**: **Inter Tight** (переменный, кириллица, сжатый смысл) — в паре с Inter Tight и Archivo как второстепенный.
- Если семейство одна: Inter Tight (её же variable-файл покрывает русский текст и небольшой дисплей на латинице); но обязателен внешний дисплей Archivo/Anton/Bebas — для сложного гротеска применимы все три.

## 2. Типографическая шкала

Расчёт на CSS--variables; все `clamp` для респонсивности, интерлиньяж для сетки (1.0–1.05 зависит от шрифта, 1.15+ для текста; читаемость на чёрном: 1.55–1.6).

```css
:root {
  /* display: огромный капс, 48px+ */
  --fs-display: clamp(3.2rem, 9.5vw, 7.8rem);
  --lh-display: 1.02;
  --ls-display: -0.02em;      /* жёсткий гротеск-капс: слегка «схлопнут» */
  --fw-display: 800;

  /* h2: секция/рубрика */
  --fs-h2: clamp(1.7rem, 4vw, 2.6rem);
  --lh-h2: 1.15;
  --ls-h2: -0.01em;
  --fw-h2: 700;

  /* h3: хедж-текст/подзаголовок */
  --fs-h3: clamp(1.15rem, 2.2vw, 1.5rem);
  --lh-h3: 1.25;
  --ls-h3: 0;
  --fw-h3: 600;

  /* body */
  --fs-body: 1rem;            /* 16px */
  --lh-body: 1.55;
  --ls-body: 0;
  --fw-body: 400;

  /* капс-лейблы (eyebrow, minitag) */
  --fs-label: 0.72rem;        /* ~11.5px */
  --lh-label: 1.35;
  --ls-label: 0.10em;         /* +0.10…0.12em — капс-лавы на фоне супер-тёмного */
  --fw-label: 600;

  /* мелкий текст */
  --fs-small: 0.81rem;        /* 13px */
  --lh-small: 1.4;
  --ls-small: 0.01em;
}
```

### Обоснование (практика: tracking по размеру и регистру)

- **Крупные капсы 48px+** (`--ls-display: -0.02em`, `-0.01…-0.03em`): плавильное лицо гротеска расширено относительно масштаба; без отрывов капс «пытаются» слипаться. Ограничение: за −0.04em буквы начинают сталкиваться и падает скорость чтения — если нужно меньше, выбираем другой дисплей[1][3].
- **Капс-лейблы 11–14px в регистре all-caps**: одинаковые по высоте буквы без разрядки слипаются (отсутствие верхних/нижних вылетов); нужна **+0.10…+0.12em** — именно эту величину выбирают для мелких лейблов, чтобы их можно было одновременно прочитать на супер-тёмном и газетном фоне[1][2][3].
- **Тело** — `0` (дизайнер семейства оптимизировал для чтения); отрывки в параграфах = неоткуда взятая разрядка.
- **Проверка на огромных капсах**: `letter-spacing: -0.02em` в `em` масштабируется с размером шрифта автоматически (одно объявление, одно правило)[4].

### Пример композиции на два шрифта

```css
.display-anton {
  font-family: 'Anton', 'Inter Tight', sans-serif;
  font-weight: 400;               /* Anton — статичный 400 */
  font-size: var(--fs-display);
  line-height: var(--lh-display);
  letter-spacing: var(--ls-display);
  text-transform: uppercase;
}
.display-archivo {
  font-family: 'Archivo', sans-serif;
  font-variation-settings: 'wght' 800, 'wdth' 125;
  font-size: var(--fs-display);
  line-height: var(--lh-display);
  letter-spacing: var(--ls-display);
  text-transform: uppercase;
}
.body-inter {
  font-family: 'Inter Tight', sans-serif;
  font-weight: 400;               /* или 500/600 по смыслу */
  font-size: var(--fs-body);
  line-height: var(--lh-body);
}
```

## 3. WCAG-контраст для палитры

Метод: относительная яркость luminances (0.2126·R + 0.7152·G + 0.0722·B, линейная модель sRGB), соотношение `(L1+0.05)/(L2+0.05)`.
Критерии WCAG 2.2 SC 1.4.3: AA — нормальный текст ≥ 4.5:1, крупный (≥24px или ≥18.66px жирный) ≥ 3:1; AAA — 7:1 и 4.5:1 [5][6].

| Пар пара | FG / BG | Отношение | AA норма | AA крупный | AAA норма | AAA крупный | Использование |
|---|---|---|---|---|---|---|---|
| Белый на чёрном | #F9F9F9 / #000 | **19.95:1** | ✓ | ✓ | ✓ | ✓ | Только текст светлых блоков |
| Чёрный на оранжевом | #000 / #E85002 | **5.58:1** | ✓ | ✓ | ✗ | ✓ | Текст на оранжевом — чёрный |
| Белый на оранжевом | #F9F9F9 / #E85002 | **3.57:1** | ✗ | ✓ | ✗ | ✗ | Только крупный ≥24px; мелкий — запрещено |
| Белый на золоте | #F9F9F9 / #C10801 | **6.04:1** | ✓ | ✓ | ✗ | ✓ | Заголовки/лейблы на золотом фоне |
| Чёрный на кремовом | #000 / #D9C3AB | **12.34:1** | ✓ | ✓ | ✓ | ✓ | Текст на светлых градиентах |
| Серый #A7A7A7 на чёрном | #A7A7A7 / #000 | **8.73:1** | ✓ | ✓ | ✓ | ✓ | Второстепенный текст — норма |
| Белый на тёмном-сером | #F9F9F9 / #333333 | **12.00:1** | ✓ | ✓ | ✓ | ✓ | Второстепенный текст |
| #646464 на чёрном | #646464 / #000 | **3.55:1** | ✗ | ✓ | ✗ | ✗ | Только крупный текст; мелкий — нельзя |
| #A7A7A7 на #333333 | #A7A7A7 / #333333 | **5.25:1** | ✓ | ✓ | ✗ | ✓ | Второстепенный на тёмной панели |
| #646464 на #333333 | #646464 / #333333 | **2.14:1** | ✗ | ✗ | ✗ | ✗ | **Запрещено** (в т.ч. крупный) |
| #646464 на белом | #646464 / #F9F9F9 | **5.62:1** | ✓ | ✓ | ✗ | ✓ | Светлая тема — мелкий текст |
| Серый на золото | #A7A7A7 / #C10801 | **2.64:1** | ✗ | ✗ | ✗ | ✗ | **Запрещено** |
| Белый на #F16001 | #F9F9F9 / #F16001 | **3.11:1** | ✗ | ✓ | ✗ | ✗ | Только крупный; лучше #000 |
| Крем на оранжевом | #D9C3AB / #E85002 | **2.21:1** | ✗ | ✗ | ✗ | ✗ | **Запрещено** |

### Итог по применению

- **Нельзя использовать для мелкого текста (< 18.66px / 24px не жирный)**: белый на #E85002 (3.57:1), белый на #F16001 (3.11:1), #646464 на #000 (3.55:1), серый на золото (2.64:1), #646464 на #333333 (2.14:1), крем на оранжевом (2.21:1).
- **Можно только для крупного** (≥24px или ≥18.66px жирный): белый на #E85002 (3.57:1), белый на #F16001 (3.11:1), #646464 на #000 (3.55:1), серый на #C10801 (2.64:1 — не рекомендуется, лейбл выглядит маринованным).
- **Главные пары**: белый на чёрном 19.95:1 — золотой стандарт; чёрный на #E85002 5.58:1 — единственный чёрный на акценте вариант, который проходит AA нормального текста; #A7A7A7 на #000 8.73:1 — безопасный второй тон для второстепенного текста.
- Для безопасности в светлой теме: #646464 на #F9F9F9 5.62:1 — минимально-нормальный выбор; #A7A7A7 на чёрном 8.73:1 — в тёмной.

## 4. CSS/SVG-техники без растровых картинок

### 4.1 Зерно (feTurbulence) — статический SVG-шум

```css
.grain::after {
  content: "";
  position: fixed; inset: 0;
  z-index: 9999;
  pointer-events: none;          /* не ловить события */
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.06'/%3E%3C/svg%3E");
  mix-blend-mode: overlay;       /* тёмный фон: зерно читается, на белом почти невидимо */
}
```

Примечание: `mix-blend-mode` разрывает связь с backdrop — работает только на экране, если конструкция не заливается в отдельной вложенной стек-контексте с `opacity`/transform.

### 4.2 Глоу-полусфера (radial) + текст

```css
.hero::before {                   /* «солнечный луч» от 30% высоты */
  content: ""; position: absolute; inset: 0;
  pointer-events: none;
  background: radial-gradient(120% 70% at 50% 28%, rgba(232,80,2,.22) 0%, rgba(232,80,2,0) 55%);
}
.orb-glow {
  filter: drop-shadow(0 0 8px rgba(232,80,2,.35))   /* элементы с прозрачной обводкой */
        drop-shadow(0 0 24px rgba(232,80,2,.18));
}
```

Сложно, но `drop-shadow` следует реальной контуральной маске, в отличие от `box-shadow`, который растягивается по рамке.

### 4.3 Градиентный «меш» из 3–4 стопов

```css
.bg-mesh {
  background:
    linear-gradient(160deg, #0000 0%, #000 16%, #C10801 43%, #F16001 67%, #D9C3AB 100%);
}
```

Плоские стопы #0000 в начале/конце скрывают градиент в отсуп; если нужен «сетчатый» микс, накладывайте слой `rgba(232,80,2,.06)` поверх. Весь градиент в RGB-интерполяции запахивает в серый; для межцветовых переходов предпочтительнее `color-mix(in oklch, #F16001 55%, transparent)` или отдельные слои. Запас: фон без градиента (flat #000), чтобы описать, что делает градиент, — если не различим на ретраит-режиме, убираем[7][8].

### 4.4 Стеклянная карточка

```css
.glass {
  background: rgba(255,255,255,.08);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,.28);   /* край стекла */
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,.35);    /* поднятие */
}
```

Физика: полупрозрачная заливка + размытие заднего плана + тонкая светлая рамка + тень = полосатый «чаша» на странице. На тёмном стеке используйте `rgba(255,255,255,.05…0.12)` (бледный белый), чтобы не засветить[9][10].

### 4.5 Плавное появление

```css
.reveal { animation: fadeUp .55s ease-out both; }
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: none; }
}
@media (prefers-reduced-motion: reduce) {
  .reveal { animation: none; opacity: 1; }   /* не видимое состояние!
                                                /* без opacity:1 блок застрянет при opacity:0 от from[11][12] */
}
```

JS-триггер (IntersectionObserver) — опционально; CSS-анимации меняются на `opacity`/`transform` только (композиттор-режиссёр, 600 мс — максимум), без перерисовки текста[13].

### Подводные камни

- **backdrop-filter**: в Safari требует `-webkit-` префикс, на слабых устройствах дорогая (GPU-слой на каждый карточку); используйте максимум 3–4 карточки, `prefers-reduced-motion` не отменяет blur, fallback = твёрдая заливка rgba[9][10].
- **Зерно**: `filter: url(#grain)` на корневой секции грузит всю страницу в отдельный графический слой; статический `::after` с data-URI кэшируется браузером после первого растрования, а анимация `baseFrequency`/`seed` каждый кадр рендерит заново — запрещена[14][15][16].
- **Градиент/глоу под текстом**: читаемость падает неограниченно; хороший приём — толстая сплошная `rgba(0,0,0,.35–.6)`, когда текст опирается на чёрную полосу, а градиент держится между блоками[7][17].
- **Свечение 3 слоёв**: яркий ядро + фон + решётка — иначе эффект мерцает; на чёрном фоне используйте беловую «оболочку» 4–8px blur, затем оранжевую в масштабе — чёрный не смешивается с цветом[18].

## 5. Антипаттерны тёмных оранжевых лендингов

1. **Оранжевый текст под маленьким капсом на чёрном** — `white` на #E85002 = 3.57:1, не проходит AA нормального текста; на больших капсах читается «дёшево», как ошибка в дизайне, а не как акцент. Используйте чёрный `#000` на оранжевом (5.58:1) или передержанный/тёмный оранжевый, если белый необходим[19].
2. **Градиент в каждой секции + затемнение под текстом как глоу** — «фон слишком худо»; оставляем градиент на уровне лейаута, а текст надевает сплошная скир rgba(0,0,0,.45), иначе парсится как полупрозрачный экран, не как объём[7][17].
3. **Акцент в каждом блоке одинаковый** — перегруженность: 3–4 глянца и 1 красный в секциях; акцент-ловушка: оранжевый палец в паре с белым/серым; если в каждой секции выделен он сам, он становится визуальным шумом[20][21].
4. **Стекло во всех карточках + зерно + glow** — совмещённость дёшевых эффектов: каждый элемент в себе, страница как игла в сноп. Ограничить glass 2–3 плавающих карточки, зерно 0.04–0.10, glow только у хита[20][22].
5. **Анимированный/сильный грамм (grain)** — выглядит как грязь и постоянно отрисовывается; в неудачном случае в логах браузера отображается перерисовка всего экрана. Статический шум opacity ≤ 0.10, без анимации, через pseudo-элемент без pointer-events[14][15][16].
6. **Чистый #000 + #F9F9F9** — на крупных капсах видна «галька» (halo) — световые обводки вокруг букв на границе кадра; заменить #0D0D0D/абсолютно тёмный серый, а текст сделать #F9F9F9 с минусами 1–2%[23].
7. **Значение грубого цвета без дополнительного индикатора** — оранжевый ссылку/иконку только по цвету: доступность + «дёшёвый» инстинкт. Ставим подчёркивание, стрелку или иконку-признак, подстраивая цвет к контрасту[20].

## 6. Чек-лист приёмки нового стиля

1. **Контраст WCAG 2.2 AA** — каждый текстовый пар: обычный ≥ 4.5:1, крупный ≥ 3:1; AAA: 7:1 / 4.5:1 (сверять с таблицей §3; пары, не вошедшие в чек, не выкладывать).
2. **Оранж как текст** — #E85002 не используется как цвет теста под 24px жирным; варианты на оранжевом: чёрный текст (5.58:1), или акцент ≥24px (3.57:1 большим), корректировка цвета до #D84400 и выше.
3. **Трекинг** — h1: −0.02em…−0.03em; h2: −0.01em; капс-лейблы: +0.10…+0.12em; body 0; проверка отображения на разных разрешениях (нет столбцов/слипания).
4. **Шрифты** — 6 локальных файлов в /fonts, `@font-face` без внешних подключений (no Google Fonts `<link>`), `font-display: swap`; Inter Tight как кириллическая основа, дисплейные семейства только для заголовков; отображение кириллицы в Safari/FF проверено.
5. **Грануляция** — opacity ≤ 0.10, статический SVG, `pointer-events: none`, z-index выше самого низа; в Chrome/FF/Открытом Safari без анимации фильтра, без падения FPS на мобильном.
6. **Backdrop-filter** — ≤3 карточки, -webkit- префикс, fallback `background: rgba(...)`; гладкость в iOS Safari 15+.

7. **Градиентный меш** — ≤3–4 стопов, палитра не размывается в серый, монотонный режим — фон без градиента читается (включая фокус-тест с отключенным CSS).
8. **Входные анимации** — длительность ≤ 600 мс, только `opacity`+`transform`, безJS-анимации в `prefers-reduced-motion: reduce` и переход `scroll-behavior: auto`, без авто-медиа.
9. **Живой контент** — текст под градиентом/глоу всегда за명세вается сплошной скир; чек: скриншот светлой секции без привязки текста к фону — фон заметно меняет окраску.
10. **Тест-завершённость** — отрисовка на 2 устройствах (десктоп + мобиль) и 2 масштаба; контраст красного фона №646464/№333333 на #E85002 и #D9C3AB; фокус-индикаторы видимые (≥3:1) и независимые от цвета[20].

## Источники

[1] Lettertype — Kerning, Tracking & Leading: https://lettertype.org/blog/kerning-tracking-leading-typography-guide  
[2] WhatFontFinder — Letter Spacing Converter: https://whatfontfinder.com/letter-spacing-converter/  
[3] Thecsiz / tastemaker — Tracking by Size & Case: https://github.com/Thecsiz/tastemaker/blob/main/skills/tastemaker/kb/craft/type-hierarchy/CR-104-tracking-and-case.md  
[4] dev.to — letter-spacing and word-spacing: https://dev.to/bm_lm_a5b33702d6aa3271c49/letter-spacing-and-word-spacing-the-css-properties-doing-optical-work-48i7  
[5] W3C WCAG 2.2 — Contrast (Minimum) SC 1.4.3: https://www.w3.org/TR/WCAG22/#visual-presentation  
[6] WebAIM Contrast Checker: https://webaim.org/articles/contrast/  
[7] dev.to — Create a Gradient Color Palette (avoid gradients under body text): https://dev.to/gavin2020/how-to-create-a-gradient-color-palette-for-your-brand-2026-guide-4550  
[8] ColorArchive — Gradient Color Palette: https://colorarchive.org/guides/gradient-color-palette/  
[9] WPDean — CSS Glassmorphism 16 Examples + 3-Line Recipe: https://wpdean.com/css-glassmorphism/  
[10] Marko Denic — CSS Glass Effect (frosted glass): https://markodetic.com/snippets/css/glass-effect/  
[11] Verdigris — Reduced Motion Guide: https://design.verdigris.co/categories/animation/reduced-motion  
[12] Grizzly Peak Software — CSS Animation Techniques: https://www.grizzlypeaksoftware.com/library/css-animation-techniques-with-javascript-triggers-s5kflz0m  
[13] Grizzly Peak Software — CSS Animation Techniques (transitions/IO): https://www.grizzlypeaksoftware.com/library/css-animation-techniques-with-javascript-triggers-s5kflz0m  
[14] Empire UI — Grain & Noise Texture in CSS: https://empire-ui.com/blog/grain-texture-css  
[15] CodeFronts — 20 Tailwind CSS Grain Texture: https://codefronts.com/design-styles/tailwind-css-grain-texture/  
[16] Effect.Labs — Noise Overlay: https://effect-labs.com/en/effects/backgrounds/noise-overlay.html  
[17] dev.to — Create a Gradient Color Palette (gradient under text): https://dev.to/gavin2020/how-to-create-a-gradient-color-palette-for-your-brand-2026-guide-4550  
[18] Empire UI — Neon Glow Effect in CSS: https://empire-ui.com/blog/neon-glow-css  
[19] Dennis Deacon — Why Orange Is an Accessibility Trap: https://www.dennisdeacon.com/accessibility/why-orange-is-an-accessibility-trap-and-what-to-do-instead/  
[20] OctoGenius — Landing Page Craft (anti-patterns): https://octomind.run/tap/skills/markup-landing-page  
[21] HorizonX — Dark UI Design in 2026: https://horizonx.so/es/blog/dark-ui-design-guide-2026  
[22] Effect.Labs — Glass Card: https://effect-labs.com/en/effects/glassmorphism/glass-card.html  
[23] LanderKit — Dark mode on a landing page: https://landerkit.fr/en/blog/mode-sombre-landing-page-conversion  
[24] Google Fonts specimens: https://fonts.google.com/specimen/Archivo · https://fonts.google.com/specimen/Anton · https://fonts.google.com/specimen/Inter+Tight · https://fonts.google.com/specimen/Space+Grotesk · https://fonts.google.com/specimen/Bebas+Neue  
[25] Google Fonts repo (raw): https://github.com/google/fonts/tree/main/ofl  
