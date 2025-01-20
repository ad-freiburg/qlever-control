// Important Global variables
var sparqlEngines = [];
var execTreeEngines = [];
var kbs = [];
var outputUrl = window.location.pathname.replace("www", "output");
var performanceDataPerKb = {};
var comparisonTables = {};

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
 * Generates the file URL for the query log yaml based on the given SPARQL engine and knowledge base.
 *
 * @param {string} engine - The SPARQL engine (e.g., 'qlever').
 * @param {string} kb - The knowledge base (e.g., 'sp2b').
 * @returns {string} The file URL for the query log.
 */
function getQueryLog(engine, kb) {
  return `${kb}.${engine}.queries.executed.yml`;
}

/**
 * Generates the file URL for the eval log tsv based on the given SPARQL engine and knowledge base.
 *
 * @param {string} engine - The SPARQL engine (e.g., 'qlever').
 * @param {string} kb - The knowledge base (e.g., 'sp2b').
 * @returns {string} The file URL for the eval log.
 */
function getEvalLog(engine, kb) {
  return `${kb}.${engine}.queries.results.tsv`;
}

/**
 * Generates the file URL for the fail log txt based on the given SPARQL engine and knowledge base.
 *
 * @param {string} engine - The SPARQL engine (e.g., 'qlever').
 * @param {string} kb - The knowledge base (e.g., 'sp2b').
 * @returns {string} The file URL for the failure log.
 */
function getFailLog(engine, kb) {
  return `${kb}.${engine}.queries.fail.txt`;
}

/**
 * Fetches and processes a YAML file from a specified URL.
 *
 * @async
 * @param {string} yamlFileUrl - The URL of the YAML file to fetch.
 * @returns {Promise<Object[]>} A promise that resolves to an array of objects parsed from the YAML file.
 * Will log an error if fetching or processing the YAML file fails.
 */
async function getYamlData(yamlFileUrl) {
  // Fetch the YAML file and process its content
  try {
    const response = await fetch(outputUrl + yamlFileUrl);
    const yamlContent = await response.text();
    // Split the content into rows
    const data = jsyaml.loadAll(yamlContent);
    return data;
  } catch (error) {
    console.error("Error fetching or processing YAML file:", error);
  }
}

/**
 * Processes the content of a TSV file and calculates various statistics.
 *
 * @param {string} tsvContent - The content of the TSV file as a string.
 * @returns {Object} An object containing parsed data, statistical metrics, and query performance analysis.
 * Will log an error if processing the TSV content fails.
 */
function getTsvData(tsvContent) {
  // Fetch the TSV file and process its content
  try {
    // Split the content into rows
    const rows = tsvContent.replace(/\r/g, "").trim().split("\n");

    // Parse the header row
    const headers = rows[0].split("\t");

    // Initialize an array to hold data objects
    const data = [];
    const result = {};

    let queryTimeArray = [];
    let totalTime = 0;
    let queries_under_1s = 0;
    let queries_over_5s = 0;
    let failed_queries = 0;
    // Iterate through the remaining rows
    for (let i = 1; i < rows.length; i++) {
      const values = rows[i].split("\t");
      const entry = {};

      // Create an object with headers as keys and values as values
      for (let j = 0; j < headers.length; j++) {
        entry[headers[j]] = values[j];
      }
      let query_time = parseFloat(values[2]);
      queryTimeArray.push(query_time);
      totalTime += query_time;
      if (values[3] == "True") {
        failed_queries++;
      } else {
        if (query_time < 1000) {
          queries_under_1s++;
        }
        if (query_time > 5000) {
          queries_over_5s++;
        }
      }

      data.push(entry);
    }

    result.data = data; // The array of parsed data objects.
    result.avgTime = totalTime / (rows.length - 1) / 1000; // The average query time in seconds.
    result.medianTime = median(queryTimeArray) / 1000; //The median query time in seconds.
    // Percentage of queries executed under 1 second.
    result.under_1s = (queries_under_1s / (rows.length - 1)) * 100;
    // Percentage of queries executed over 5 seconds.
    result.over_5s = (queries_over_5s / (rows.length - 1)) * 100;
    result.failed = (failed_queries / (rows.length - 1)) * 100; // Percentage of failed queries.
    // Percentage of queries executed between 1 and 5 seconds.
    result.between_1_to_5s = 100 - result.under_1s - result.over_5s - result.failed;
    return result;
  } catch (error) {
    console.error("Error processing TSV file:", error);
  }
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
