/**
 * List of query statistics keys (values unused, so just keys kept)
 */
const QUERY_STATS_KEYS = ["ameanTime", "gmeanTime", "medianTime", "under1s", "between1to5s", "over5s", "failed"];

/**
 * Given a knowledge base (kb), get all query stats for each engine to display
 * on the main page of evaluation web app as a table.
 *
 * @param {Object<string, Object<string, any>>} performanceData - The performance data for all KBs and engines
 * @param {string} kb - The knowledge base key to extract data for
 * @returns {Object<string, Array>} Object mapping metric keys and engine names to arrays of values
 */
function getAllQueryStatsByKb(performanceData, kb) {
  const enginesDict = performanceData[kb];
  const enginesDictForTable = { engine_name: [] };

  // Initialize arrays for all metric keys
  QUERY_STATS_KEYS.forEach((key) => {
    enginesDictForTable[key] = [];
  });

  for (const [engine, engineStats] of Object.entries(enginesDict)) {
    enginesDictForTable.engine_name.push(capitalize(engine));
    for (const metricKey of QUERY_STATS_KEYS) {
      enginesDictForTable[metricKey].push(engineStats[metricKey]);
    }
  }
  return enginesDictForTable;
}

/**
 * Capitalizes the first letter of a string.
 *
 * @param {string} str - Input string
 * @returns {string} Capitalized string
 */
function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Extract the core value from a SPARQL result value.
 *
 * @param {string | string[]} sparqlValue - The raw SPARQL value or list of values
 * @returns {string} The extracted core value or empty string if none
 */
function extractCoreValue(sparqlValue) {
  if (Array.isArray(sparqlValue)) {
    if (sparqlValue.length === 0) return "";
    sparqlValue = sparqlValue[0];
  }

  if (typeof sparqlValue !== "string" || !sparqlValue.trim()) return "";

  // URI enclosed in angle brackets
  if (sparqlValue.startsWith("<") && sparqlValue.endsWith(">")) {
    return sparqlValue.slice(1, -1);
  }

  // Literal string like "\"Some value\""
  const literalMatch = sparqlValue.match(/^"((?:[^"\\]|\\.)*)"/);
  if (literalMatch) {
    const raw = literalMatch[1];
    return raw.replace(/\\(.)/g, "$1");
  }

  // Fallback - return as is
  return sparqlValue;
}

/**
 * Extracts a single result string from query data if exactly one result exists.
 *
 * @param {Object} queryData - Single query data object
 * @returns {string | null} Formatted single result or null if not applicable
 */
function getSingleResult(queryData) {
  let resultSize = queryData.result_size ?? 0;
  let singleResult = null;

  if (
    resultSize === 1 &&
    Array.isArray(queryData.headers) &&
    queryData.headers.length === 1 &&
    Array.isArray(queryData.results) &&
    queryData.results.length === 1
  ) {
    singleResult = extractCoreValue(queryData.results[0]);
    // Try formatting as int with commas
    const intVal = parseInt(singleResult, 10);
    if (!isNaN(intVal)) {
      singleResult = intVal.toLocaleString();
    }
  }
  return singleResult;
}

/**
 * Extracts runtime and related query info for a given knowledge base and engine.
 *
 * @param {Object<string, Object<string, any>>} performanceData - Performance data object
 * @param {string} kb - Knowledge base name
 * @param {string} engine - Engine name
 * @returns {Object<string, Array>} Object containing arrays for query, runtime, failed, and result_size
 */
function getQueryRuntimes(performanceData, kb, engine) {
  const allQueriesData = performanceData[kb][engine].queries;
  const queryRuntimes = {
    query: [],
    runtime: [],
    failed: [],
    result_size: [],
  };

  for (const queryData of allQueriesData) {
    queryRuntimes.query.push(queryData.query);
    const runtime = Number(queryData.runtime_info.client_time.toFixed(2));
    queryRuntimes.runtime.push(runtime);

    const failed = typeof queryData.results === "string" || (queryData.headers?.length ?? 0) === 0;
    queryRuntimes.failed.push(failed);

    const resultSize = queryData.result_size ?? 0;
    const singleResult = getSingleResult(queryData);

    const resultSizeToDisplay = singleResult === null ? resultSize.toLocaleString() : `1 [${singleResult}]`;

    queryRuntimes.result_size.push(resultSizeToDisplay);
  }
  return queryRuntimes;
}

/**
 * Converts query results represented as a list of lists into a dictionary
 * mapping headers to their respective columns (lists).
 *
 * @param {string[]} headers - List of header strings
 * @param {string[][]} queryResults - List of query results (each result is a list of strings)
 * @returns {Object<string, string[]>} Object mapping header names to lists of column values
 */
function getQueryResultsDict(headers, queryResults) {
  const queryResultsLists = headers.map(() => []);

  for (const result of queryResults) {
    for (let i = 0; i < headers.length; i++) {
      queryResultsLists[i].push(result[i]);
    }
  }

  const queryResultsDict = {};
  headers.forEach((header, i) => {
    queryResultsDict[header] = queryResultsLists[i];
  });

  return queryResultsDict;
}


document.addEventListener('DOMContentLoaded', async () => {
  const container = document.getElementById('main-table-container');

  try {
    const response = await fetch('/yaml_data');
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const performanceData = await response.json();

    // Clear container if any existing content
    container.innerHTML = '';

    // For each knowledge base (kb) key in performanceData
    for (const kb of Object.keys(performanceData)) {
      // Create section wrapper
      const section = document.createElement('div');
      section.className = 'kg-section';

      // Header with KB name and a dummy compare button
      const header = document.createElement('div');
      header.className = 'kg-header';

      const title = document.createElement('h5');
      title.textContent = capitalize(kb);
      title.style.fontWeight = "bold";

      const compareBtn = document.createElement('button');
      compareBtn.className = 'btn btn-outline-primary btn-sm';
      compareBtn.textContent = 'Compare Results';
      compareBtn.onclick = () => alert(`Compare results for ${kb}`);

      header.appendChild(title);
      header.appendChild(compareBtn);

      // Grid div with ag-theme-alpine styling
      const gridDiv = document.createElement('div');
      gridDiv.className = 'ag-theme-balham';
      gridDiv.style.height = 'auto';  // adjust height as needed
      gridDiv.style.width = '100%';

      // Append header and grid div to section
      section.appendChild(header);
      section.appendChild(gridDiv);
      container.appendChild(section);

      // Get table data from function you provided
      const tableData = getAllQueryStatsByKb(performanceData, kb);

      // Build column definitions for ag-grid dynamically
      const columnDefs = Object.keys(tableData).map((colKey) => ({
        headerName: colKey === 'engine_name' ? 'Engine Name' : colKey,
        field: colKey,
        sortable: true,
        filter: true,
        resizable: true,
        flex: 1,
      }));

      // Prepare row data as array of objects for ag-grid
      // tableData is {colName: [val, val, ...], ...}
      // We convert to [{engine_name: ..., ameanTime: ..., ...}, ...]
      const rowCount = tableData.engine_name.length;
      const rowData = Array.from({ length: rowCount }, (_, i) => {
        const row = {};
        for (const col of Object.keys(tableData)) {
          row[col] = tableData[col][i];
        }
        return row;
      });

      // Initialize ag-Grid instance
      agGrid.createGrid(gridDiv, {
        columnDefs,
        rowData,
        defaultColDef: {
          sortable: true,
          filter: true,
          resizable: true,
          flex: 1,
          minWidth: 100,
        },
        domLayout: "autoHeight",
      });
    }
  } catch (err) {
    console.error('Error loading /yaml_data:', err);
    container.innerHTML = `<div class="alert alert-danger">Failed to load data.</div>`;
  }
});

