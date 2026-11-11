/* Переключение языка без сборки и без fetch: словарь лежит в window.I18N (i18n.js).
   Работает по file:// — только DOM API. */
(function () {
  'use strict';

  var STORAGE_KEY = 'portfolio.lang';
  var DEFAULT_LANG = 'ru';
  var LANGS = ['ru', 'en'];

  function readStoredLang() {
    try {
      var saved = window.localStorage.getItem(STORAGE_KEY);
      return LANGS.indexOf(saved) !== -1 ? saved : null;
    } catch (e) {
      return null;
    }
  }

  function storeLang(lang) {
    try {
      window.localStorage.setItem(STORAGE_KEY, lang);
    } catch (e) {
      /* приватный режим или file:// с запретом storage — просто игнорируем */
    }
  }

  function getDictionary(page, lang) {
    var i18n = window.I18N || {};
    var pageDict = i18n[page] || {};
    return pageDict[lang] || {};
  }

  function applyLang(lang) {
    var page = document.body.getAttribute('data-page') || '';
    var dict = getDictionary(page, lang);
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
  }

  function currentLang() {
    return document.documentElement.getAttribute('data-lang') === 'en' ? 'en' : DEFAULT_LANG;
  }

  function init() {
    var lang = readStoredLang() || DEFAULT_LANG;
    applyLang(lang);

    var toggle = document.getElementById('langToggle');
    if (!toggle) {
      return;
    }

    toggle.addEventListener('click', function () {
      var next = currentLang() === 'ru' ? 'en' : 'ru';
      applyLang(next);
      storeLang(next);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
