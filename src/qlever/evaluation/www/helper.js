// Important Global variables
var sparqlEngines = [];
var execTreeEngines = [];
var kbs = [];
var outputUrl = window.location.pathname.replace("www", "output");
var performanceDataPerKb = {};

var high_query_time_ms = 200;
var very_high_query_time_ms = 1000;

/**
 * Formats a number to include commas as thousands separators and ensures exactly two decimal places.
 *
 * @param {number} number - The number to format.
 * @returns {string} The formatted number as a string.
 */
function formatNumber(number) {
  return number.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Formats a number to include commas as thousands separators without ensuring decimal places.
 *
 * @param {number} number - The number to format.
 * @returns {string} The formatted number as a string with commas as thousands separators.
 */
function format(number) {
  return number.toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1,");
}

/**
 * Escape text for an attribute
 * Source: https://stackoverflow.com/a/77873486
 * @param {string} text
 * @returns {string}
 */
function EscapeAttribute(text) {
  return text.replace(
    /[&<>"']/g,
    (match) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
      }[match])
  );
}

/**
 * Displays the loading spinner by updating the relevant CSS classes.
 */
function showSpinner() {
  document.querySelector("#spinner").classList.remove("d-none", "d-flex");
  document.querySelector("#spinner").classList.add("d-flex");
}

/**
 * Hides the loading spinner by updating the relevant CSS classes.
 */
function hideSpinner() {
  document.querySelector("#spinner").classList.remove("d-none", "d-flex");
  document.querySelector("#spinner").classList.add("d-none");
}

/**
 * Set multiple attributes on a given DOM node dynamically.
 * Simplifies setting multiple attributes at once by iterating over a key-value pair object.
 * @param {HTMLElement} node - The DOM node on which attributes will be set.
 * @param {Object} attributes - An object containing key-value pairs of attributes to set.
 */
function setAttributes(node, attributes) {
  if (node) {
    for (const [key, value] of Object.entries(attributes)) {
      node.setAttribute(key, value);
    }
  }
}

/**
 * Display a Bootstrap modal and optionally set attributes dynamically.
 * Ensures the modal is shown and adds a custom `pop-triggered` attribute for tracking purposes.
 * @param {HTMLElement} modalNode - The DOM node representing the modal to be shown.
 * @param {Object} [attributes={}] - Optional attributes to set on the modal before showing it.
 * @param {boolean} fromPopState - Is the modal being shown when pop state event is fired.
 */
function showModal(modalNode, attributes = {}, fromPopState = false) {
  if (modalNode) {
    setAttributes(modalNode, attributes);
    if (fromPopState) {
      modalNode.setAttribute("pop-triggered", true);
    }
    const modal = bootstrap.Modal.getOrCreateInstance(modalNode);
    modal.show();
  }
}

function extractCoreValue(sparqlValue) {
  if (Array.isArray(sparqlValue)) {
    if (sparqlValue.length === 0) return "";
    sparqlValue = sparqlValue[0];
  }
  if (typeof sparqlValue !== "string" || sparqlValue.trim() === "") {
    return "";
  }

  if (sparqlValue.startsWith("<") && sparqlValue.endsWith(">")) {
    // URI
    return sparqlValue.slice(1, -1);
  }

  const literalMatch = sparqlValue.match(/^"((?:[^"\\]|\\.)*)"/);
  if (literalMatch) {
    // Decode escape sequences (e.g. \" \\n etc.)
    const raw = literalMatch[1];
    return raw.replace(/\\(.)/g, "$1");
  }

  // fallback: return as-is
  return sparqlValue;
}
