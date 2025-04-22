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
 * Fetches and processes a YAML file from a specified URL.
 *
 * @async
 * @param {string} yamlFileUrl - The URL of the YAML file to fetch.
 * @returns {Promise<Object[]>} A promise that resolves to an array of objects parsed from the YAML file.
 * Will log an error if fetching or processing the YAML file fails.
 */
async function getYamlData(yamlFileUrl, headers = {}) {
  // Fetch the YAML file and process its content
  try {
    const response = await fetch(outputUrl + yamlFileUrl, { headers });
    if (!response.ok) {
      throw new Error(`Failed to fetch ${yamlFileUrl}`);
    }
    const yamlContent = await response.text();
    // Split the content into rows
    const data = jsyaml.load(yamlContent);
    return data;
  } catch (error) {
    console.error("Error fetching or processing YAML file:", error);
    return null;
  }
}

function addQueryStatistics(queryData) {
  let runtimeArray = [];
  let totalTime = 0;
  let totalLogTime = 0;
  let queriesUnder1s = 0;
  let queriesOver5s = 0;
  let failedQueries = 0;
  for (const query of queryData.queries) {
    let runtime = parseFloat(query.runtime_info.client_time);
    runtimeArray.push(runtime);
    totalTime += runtime;
    totalLogTime += Math.max(Math.log(runtime), 0.001);
    if (query.headers.length === 0 && typeof query.results == "string") {
      failedQueries++;
    } else {
      if (runtime < 1) {
        queriesUnder1s++;
      }
      if (runtime > 5) {
        queriesOver5s++;
      }
    }
  }
  let n = queryData.queries.length;
  queryData.ameanTime = totalTime / n;
  queryData.gmeanTime = Math.exp(totalLogTime / n);
  queryData.medianTime = median(runtimeArray);
  queryData.under1s = (queriesUnder1s / n) * 100;
  queryData.over5s = (queriesOver5s / n) * 100;
  queryData.failed = (failedQueries / n) * 100;
  queryData.between1to5s = 100 - queryData.under1s - queryData.over5s - queryData.failed;
}

/**
 * Processes the content of a TXT file and returns its lines as an array of strings.
 *
 * @param {string} txtContent - The content of the TXT file as a string.
 * @returns {string[]} An array of strings representing each line in the TXT file.
 * Will log an error if processing the TXT content fails.
 */
function getTxtData(txtContent) {
  // Fetch the TSV file and process its content
  try {
    // Split the content into rows
    if (!txtContent) {
      return [];
    }
    const rows = txtContent.replace(/\r/g, "").trim().split("\n");
    return rows;
  } catch (error) {
    console.error("Error processing TXT file:", error);
  }
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
 * Calculates the median value from an array of numbers.
 *
 * @param {number[]} values - An array of numbers.
 * @returns {number} The median value, or -1 if the array is empty.
 */
function median(values) {
  if (values.length === 0) {
    return -1;
  }

  values = [...values].sort((a, b) => a - b);

  const half = Math.floor(values.length / 2);

  return values.length % 2 ? values[half] : (values[half - 1] + values[half]) / 2;
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
