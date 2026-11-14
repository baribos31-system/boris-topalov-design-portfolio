/* Язык и тема — без сборки и без fetch: словарь лежит в window.I18N (i18n.js).
   Работает по file:// — только DOM API + localStorage в try/catch.
   Тема и язык независимы: <html lang="ru" data-lang="ru" data-theme="dark">. */
(function () {
  'use strict';

  var LANG_KEY = 'portfolio.lang';
  var THEME_KEY = 'portfolio.theme';
  var DEFAULT_LANG = 'ru';
  var DEFAULT_THEME = 'dark';
  var LANGS = ['ru', 'en'];
  var THEMES = ['dark', 'light'];

  /* --- storage ---------------------------------------------------------- */

  function readStored(key, allowed) {
    try {
      var saved = window.localStorage.getItem(key);
      return allowed.indexOf(saved) !== -1 ? saved : null;
    } catch (e) {
      return null;
    }
  }

  function store(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      /* приватный режим или file:// с запретом storage — просто игнорируем */
    }
  }

  /* --- dictionary ------------------------------------------------------- */

  function pageId() {
    return (document.body && document.body.getAttribute('data-page')) || '';
  }

  function dictionary(lang) {
    var i18n = window.I18N || {};
    var page = i18n[pageId()] || {};
    return page[lang] || {};
  }

  function t(lang, key, fallback) {
    var dict = dictionary(lang);
    return Object.prototype.hasOwnProperty.call(dict, key) ? dict[key] : fallback;
  }

  /* --- state ------------------------------------------------------------ */

  function currentLang() {
    return document.documentElement.getAttribute('data-lang') === 'en' ? 'en' : DEFAULT_LANG;
  }

  function currentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : DEFAULT_THEME;
  }

  /* --- language --------------------------------------------------------- */

  function applyLang(lang) {
    var dict = dictionary(lang);
    var nodes = document.querySelectorAll('[data-i18n]');
    var i;
    var key;
    var node;

    for (i = 0; i < nodes.length; i++) {
      node = nodes[i];
      key = node.getAttribute('data-i18n');
      if (key && Object.prototype.hasOwnProperty.call(dict, key)) {
        node.textContent = dict[key];
      }
    }

    document.documentElement.setAttribute('lang', lang);
    document.documentElement.setAttribute('data-lang', lang);

    var toggle = document.getElementById('langToggle');
    if (toggle) {
      /* в русском режиме кнопка показывает EN и наоборот */
      toggle.textContent = lang === 'ru' ? 'EN' : 'RU';
      toggle.setAttribute('lang', lang === 'ru' ? 'en' : 'ru');
      toggle.setAttribute('aria-label', lang === 'ru' ? 'Switch to English' : 'Переключить на русский');
    }

    /* подпись и aria-label переключателя темы тоже локализованы */
    renderThemeToggle(currentTheme(), lang);
  }

  /* --- theme ------------------------------------------------------------ */

  /* Кнопка темы — иконка (svg в разметке), поэтому текст не перезаписываем:
     обновляем только локализованный aria-label. */
  function renderThemeToggle(theme, lang) {
    var btn = document.getElementById('themeToggle');
    if (!btn) {
      return;
    }

    var toLight = theme !== 'light';

    btn.setAttribute('lang', lang);
    btn.setAttribute('aria-label', toLight
      ? t(lang, 'theme.toLight', 'Switch to light theme')
      : t(lang, 'theme.toDark', 'Switch to dark theme'));
  }

  function applyTheme(theme) {
    var next = theme === 'light' ? 'light' : DEFAULT_THEME;
    document.documentElement.setAttribute('data-theme', next);
    renderThemeToggle(next, currentLang());
  }

  /* --- init ------------------------------------------------------------- */

  function init() {
    var lang = readStored(LANG_KEY, LANGS) || DEFAULT_LANG;

    /* тема применяется до языка, чтобы aria-label сразу получил перевод */
    applyTheme(readStored(THEME_KEY, THEMES) || DEFAULT_THEME);
    applyLang(lang);

    var langToggle = document.getElementById('langToggle');
    if (langToggle) {
      langToggle.addEventListener('click', function () {
        var next = currentLang() === 'ru' ? 'en' : 'ru';
        applyLang(next);
        store(LANG_KEY, next);
      });
    }

    var themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', function () {
        var next = currentTheme() === 'light' ? 'dark' : 'light';
        applyTheme(next);
        store(THEME_KEY, next);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
