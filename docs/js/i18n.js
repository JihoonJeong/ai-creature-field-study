(function () {
  // Determine i18n JSON base path from this script's location
  // Script is at /js/i18n.js, JSON is at /i18n/ko.json
  const scriptEl = document.currentScript;
  const scriptUrl = new URL(scriptEl.src);
  const i18nBase = new URL('../i18n/', scriptUrl).href;

  const I18N = {
    lang: localStorage.getItem('lang') || 'en',
    translations: null,
    originals: new Map(),

    async init() {
      this.createToggle();
      if (this.lang === 'ko') {
        await this.load('ko');
        this.apply();
      }
    },

    async load(lang) {
      try {
        const res = await fetch(i18nBase + lang + '.json');
        if (!res.ok) throw new Error(res.status);
        this.translations = await res.json();
      } catch (e) {
        console.warn('[i18n] Failed to load translations:', e);
        this.translations = null;
      }
    },

    apply() {
      if (!this.translations) return;

      document.querySelectorAll('[data-i18n]').forEach(function(el) {
        var key = el.getAttribute('data-i18n');
        var val = I18N.resolve(key);
        if (val != null) {
          if (!I18N.originals.has(el)) I18N.originals.set(el, { type: 'text', value: el.textContent });
          el.textContent = val;
        }
      });

      document.querySelectorAll('[data-i18n-html]').forEach(function(el) {
        var key = el.getAttribute('data-i18n-html');
        var val = I18N.resolve(key);
        if (val != null) {
          if (!I18N.originals.has(el)) I18N.originals.set(el, { type: 'html', value: el.innerHTML });
          el.innerHTML = val;
        }
      });

      document.documentElement.lang = 'ko';
      this.updateToggle();
    },

    restore() {
      this.originals.forEach(function(orig, el) {
        if (orig.type === 'text') el.textContent = orig.value;
        else el.innerHTML = orig.value;
      });
      this.originals.clear();
      document.documentElement.lang = 'en';
      this.updateToggle();
    },

    resolve(key) {
      var parts = key.split('.');
      var obj = this.translations;
      for (var i = 0; i < parts.length; i++) {
        if (obj == null) return null;
        obj = obj[parts[i]];
      }
      return obj;
    },

    async toggle() {
      if (this.lang === 'en') {
        this.lang = 'ko';
        localStorage.setItem('lang', 'ko');
        if (!this.translations) await this.load('ko');
        this.apply();
      } else {
        this.lang = 'en';
        localStorage.setItem('lang', 'en');
        this.restore();
      }
    },

    createToggle() {
      var nav = document.querySelector('.nav-links');
      if (!nav) return;
      var li = document.createElement('li');
      var btn = document.createElement('button');
      btn.className = 'lang-toggle';
      btn.id = 'lang-toggle';
      btn.addEventListener('click', function() { I18N.toggle(); });
      li.appendChild(btn);
      nav.appendChild(li);
      this.updateToggle();
    },

    updateToggle() {
      var btn = document.getElementById('lang-toggle');
      if (!btn) return;
      btn.textContent = this.lang === 'en' ? '한국어' : 'EN';
      btn.setAttribute('aria-label',
        this.lang === 'en' ? 'Switch to Korean' : 'Switch to English');
    }
  };

  // Init after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { I18N.init(); });
  } else {
    I18N.init();
  }

  window.I18N = I18N;
})();
