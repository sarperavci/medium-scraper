/**
 * Utility functions for the Medium Scraper application
 */

/**
 * Truncates text to a specified limit and adds truncation indicator
 * @param {string|null|undefined} text - The text to truncate
 * @param {number} limit - The maximum length (default: 4000)
 * @returns {string} The truncated text with indicator if needed
 */
function truncate(text, limit = 4000) {
  if (text === null || text === undefined) return '';
  const s = String(text);
  return s.length > limit ? s.slice(0, limit) + '\n...\n[truncated]' : s;
}

/**
 * Gets the current date in ISO format (YYYY-MM-DD)
 * @returns {string} Current date in ISO format
 */
function getCurrentDateISO() {
  return new Date().toISOString().split('T')[0];
}

/**
 * Gets the first day of the current month in ISO format (YYYY-MM-DD)
 * @returns {string} First day of current month in ISO format
 */
function getFirstDayOfMonthISO() {
  const today = new Date();
  const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  return firstDayOfMonth.toISOString().split('T')[0];
}

/**
 * Gets the current year
 * @returns {number} Current year
 */
function getCurrentYear() {
  return new Date().getFullYear();
}

/**
 * Gets the current month (1-12)
 * @returns {number} Current month
 */
function getCurrentMonth() {
  return new Date().getMonth() + 1;
}

// Export functions for use by other modules
window.Utils = {
  truncate,
  getCurrentDateISO,
  getFirstDayOfMonthISO,
  getCurrentYear,
  getCurrentMonth
};