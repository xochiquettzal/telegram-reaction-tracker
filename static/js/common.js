// static/js/common.js

/**
 * Changes the language query parameter in the URL and reloads the page.
 * @param {string} lang - The language code (e.g., 'en', 'tr').
 */
function changeLanguage(lang) {
  const currentUrl = new URL(window.location.href);
  currentUrl.searchParams.set('lang', lang);
  window.location.href = currentUrl.toString();
}

// Add any other common JavaScript functions here in the future.
