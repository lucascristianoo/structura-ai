/**
 * Structura.AI — Theme Manager
 * Defaults to the user's device preference (prefers-color-scheme),
 * persists manual overrides via the compact navbar toggle, and notifies
 * interactive components (e.g., 2D Structural Canvas) on theme changes.
 */

const THEME_STORAGE_KEY = 'structura-theme';

class ThemeManager {
  constructor() {
    this.mediaQuery = window.matchMedia
      ? window.matchMedia('(prefers-color-scheme: dark)')
      : null;

    this.toggleBtn = null;
    this.init();
  }

  getStoredTheme() {
    try {
      const val = localStorage.getItem(THEME_STORAGE_KEY);
      return val === 'light' || val === 'dark' ? val : null;
    } catch {
      return null;
    }
  }

  getDeviceTheme() {
    return this.mediaQuery?.matches ? 'dark' : 'light';
  }

  getActiveTheme() {
    return this.getStoredTheme() || this.getDeviceTheme();
  }

  isDark() {
    return document.documentElement.classList.contains('dark');
  }

  getCssVar(name, fallback = '') {
    const val = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return val || fallback;
  }

  applyTheme(theme, { persist = false, notify = true } = {}) {
    const normalized = theme === 'dark' ? 'dark' : 'light';
    const root = document.documentElement;

    root.classList.toggle('dark', normalized === 'dark');
    root.dataset.theme = normalized;

    if (persist) {
      try {
        localStorage.setItem(THEME_STORAGE_KEY, normalized);
      } catch {
        // Ignore storage quota / privacy mode errors
      }
    }

    this.syncToggleButton(normalized);

    if (notify) {
      window.dispatchEvent(
        new CustomEvent('structura:themechange', {
          detail: { theme: normalized }
        })
      );
    }
  }

  toggle() {
    const nextTheme = this.isDark() ? 'light' : 'dark';
    this.applyTheme(nextTheme, { persist: true, notify: true });
  }

  syncToggleButton(theme = this.getActiveTheme()) {
    if (!this.toggleBtn) return;
    const isDark = theme === 'dark';
    const label = isDark ? 'Mudar para tema claro' : 'Mudar para tema escuro';
    this.toggleBtn.setAttribute('aria-label', label);
    this.toggleBtn.setAttribute('title', label);
    this.toggleBtn.setAttribute('aria-pressed', String(isDark));
  }

  init() {
    // Ensure root reflects active theme immediately
    this.applyTheme(this.getActiveTheme(), { persist: false, notify: false });

    // Track OS/device theme changes automatically when user hasn't overridden
    if (this.mediaQuery) {
      const handleDeviceChange = (e) => {
        if (!this.getStoredTheme()) {
          this.applyTheme(e.matches ? 'dark' : 'light', { persist: false, notify: true });
        }
      };

      if (this.mediaQuery.addEventListener) {
        this.mediaQuery.addEventListener('change', handleDeviceChange);
      } else if (this.mediaQuery.addListener) {
        this.mediaQuery.addListener(handleDeviceChange);
      }
    }

    const bindDom = () => {
      this.toggleBtn = document.getElementById('theme-toggle');
      if (this.toggleBtn) {
        this.syncToggleButton();
        this.toggleBtn.addEventListener('click', () => this.toggle());
      }
    };

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', bindDom);
    } else {
      bindDom();
    }
  }
}

window.StructuraTheme = new ThemeManager();
