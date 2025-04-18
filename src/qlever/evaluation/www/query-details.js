/**
 * Sets event listeners for the tabs in queryDetailsModal
 *
 * - Listens for click events on query tab buttons and handles tab switching.
 * - Controls the visibility of the modal footer based on the selected tab and content.
 */
function setListenersForQueriesTabs() {
  const modalNode = document.querySelector("#queryDetailsModal");
  // Before the modal is shown, update the url and history Stack and remove the previous table
  modalNode.addEventListener("show.bs.modal", async function () {
    const kb = modalNode.getAttribute("data-kb");
    const engine = modalNode.getAttribute("data-engine");
    const selectedQuery = modalNode.getAttribute("data-query") ? modalNode.getAttribute("data-query") : null;
    const tab = modalNode.getAttribute("data-tab") ? modalNode.getAttribute("data-tab") : null;

    if (kb && engine) {
      // If back/forward button, do nothing
      if (modalNode.getAttribute("pop-triggered")) {
        modalNode.removeAttribute("pop-triggered");
      }
      // Else Update the url params and push the page to history stack
      else {
        updateUrlAndState(kb, engine, selectedQuery, tab);
      }

      // If the kb and engine are the same as previously opened, do nothing
      const modalTitle = modalNode.querySelector(".modal-title");
      const tab1Content = modalNode.querySelector("#runtimes-tab-pane");
      if (
        modalTitle.textContent.split(" - ")[1] === engine &&
        tab1Content.querySelector(".card-title").innerHTML.split(" - ")[1]
      ) {
        return;
      }
      // Else clear the table with queries and runtimes before the modal is shown
      else {
        const tabBody = modalNode.querySelector("#queryList");
        tabBody.replaceChildren();
        // Populate modal title
        modalTitle.textContent = "SPARQL Engine - ";
        // Populate Knowledge base
        tab1Content.querySelector(".card-title").innerHTML = "Knowledge Graph - ";
        //bootstrap.Tab.getOrCreateInstance(document.querySelector("#runtimes-tab")).show();
        showTab(0);
      }
    }
  });

  // After the modal is shown, populate the modal based on kb and engine attributes
  modalNode.addEventListener("shown.bs.modal", async function () {
    const kb = modalNode.getAttribute("data-kb");
    const engine = modalNode.getAttribute("data-engine");
    const selectedQuery = modalNode.getAttribute("data-query") ? parseInt(modalNode.getAttribute("data-query")) : null;
    const tab = modalNode.getAttribute("data-tab") ? parseInt(modalNode.getAttribute("data-tab")) : null;
    if (kb && engine) {
      await openQueryDetailsModal(kb, engine, selectedQuery, tab);
    }
    const resultSizeCheckbox = document.querySelector("#showResultSizeQd");

    if (!resultSizeCheckbox.hasEventListener) {
      resultSizeCheckbox.addEventListener("change", function () {
        const tdElements = modalNode.querySelectorAll("td");
        if (resultSizeCheckbox.checked) {
          tdElements.forEach((td) => {
            const resultSizeDiv = td.querySelector("div.text-muted.small");
            resultSizeDiv?.classList.remove("d-none");
          });
        } else {
          tdElements.forEach((td) => {
            const resultSizeDiv = td.querySelector("div.text-muted.small");
            resultSizeDiv?.classList.add("d-none");
          });
        }
      });
      resultSizeCheckbox.hasEventListener = true;
    }
  });

  // Handle the modal's `hidden.bs.modal` event
  modalNode.addEventListener("hidden.bs.modal", function () {
    // Don't execute any url or state based code when back/forward button clicked
    if (modalNode.getAttribute("pop-triggered")) {
      modalNode.removeAttribute("pop-triggered");
      return;
    }
    // Remove modal-related parameters from the URL
    const url = new URL(window.location);
    url.searchParams.delete("page");
    url.searchParams.delete("kb");
    url.searchParams.delete("engine");
    url.searchParams.delete("q");
    url.searchParams.delete("t");
    window.history.pushState({ page: "main" }, "", url);
  });

  const triggerTabList = document.querySelectorAll("#myTab button");
  triggerTabList.forEach((triggerEl, index) => {
    triggerEl.addEventListener("click", (event) => {
      event.preventDefault();
      showTab(index);
      const urlParams = new URLSearchParams(window.location.search);
      updateUrlAndState(urlParams.get("kb"), urlParams.get("engine"), urlParams.get("q"), index);
    });
  });

  // Adds functionality to buttons in the modal footer for zooming in/out the execution tree
  modalNode.querySelector(".modal-footer").addEventListener("click", function (event) {
    if (event.target.tagName === "BUTTON") {
      const purpose = event.target.id;
      const treeId = "#result-tree";
      const tree = document.querySelector(treeId);
      const currentFontSize = tree.querySelector(".node[class*=font-size-]").className.match(/font-size-(\d+)/)[1];
      generateExecutionTree(null, purpose, treeId, Number.parseInt(currentFontSize));
    }
  });
}

function updateUrlAndState(kb, engine, selectedQuery, tab) {
  const url = new URL(window.location);
  url.searchParams.set("page", "queriesDetails");
  url.searchParams.set("kb", kb);
  url.searchParams.set("engine", engine);
  const state = { page: "queriesDetails", kb: kb, engine: engine };
  selectedQuery !== null && (state.q = selectedQuery.toString()) && url.searchParams.set("q", selectedQuery.toString());
  tab !== null && (state.t = tab.toString()) && url.searchParams.set("t", tab.toString());
  // If this page is directly opened from url, replace the null state in history stack
  if (window.history.state === null) {
    window.history.replaceState(state, "", url);
  } else {
    window.history.pushState(state, "", url);
  }
}

function fixUrlAndState(totalQueries, selectedQuery, tab) {
  const url = new URL(window.location);
  let updateState = false;
  if (selectedQuery === null || selectedQuery >= totalQueries) {
    url.searchParams.delete("q");
    updateState = true;
    selectedQuery = null;
  }
  if (tab === null) {
    url.searchParams.delete("t");
    updateState = true;
  }
  if (updateState) {
    const currentState = window.history.state;
    const newState = { ...currentState };
    selectedQuery === null && delete newState["q"];
    tab === null && delete newState["t"];
    history.replaceState(newState, "", url);
  }
  return { q: selectedQuery, t: tab };
}

/**
 * Handles the click event on a row in the cards on main page.
 *
 * Set the kb and engine attribute based on the row clicked on by the user and open the modal
 *
 * @async
 * @param {Event} event - The click event triggered by selecting a row.
 */
async function handleRowClick(event) {
  if (
    event.target.classList.contains("row-checkbox") ||
    event.target.firstElementChild?.classList.contains("row-checkbox")
  ) {
    return;
  }
  const kb = event.currentTarget.closest(".card").querySelector("h5").innerHTML.toLowerCase();
  const engine = event.currentTarget.children[1].innerHTML.toLowerCase();
  const modalNode = document.querySelector("#queryDetailsModal");
  modalNode.setAttribute("data-kb", kb);
  modalNode.setAttribute("data-engine", engine);
  modalNode.setAttribute("data-query", "");
  modalNode.setAttribute("data-tab", "");
  showModal(modalNode);
}

/**
 * - Fetches the query log and results based on the selected knowledge base (KB) and engine.
 * - Updates the modal content and displays the query details.
 * - Manages the state of the query execution tree and tab content.
 *
 * @async
 * @param {string} kb - The selected knowledge base
 * @param {string} engine - The selected sparql engine
 * @param {number} selectedQuery - Selected Query index in runtimes table, if any
 * @param {number} tabToOpen - index of the tab to show
 */
async function openQueryDetailsModal(kb, engine, selectedQuery, tabToOpen) {
  const modalNode = document.getElementById("queryDetailsModal");

  // If the kb and engine are the same as previously opened, do nothing and display the modal as it is.
  const modalTitle = modalNode.querySelector(".modal-title");
  const tab1Content = modalNode.querySelector("#runtimes-tab-pane");
  if (modalTitle.textContent.includes(engine) && tab1Content.querySelector(".card-title").innerHTML.includes(kb)) {
    tabToOpen === null ? showTab(0) : showTab(tabToOpen);
    return;
  }

  // Fetch and display the runtime table with all queries and populate and display the first tab
  showSpinner();
  // Populate modal title
  modalTitle.textContent = "SPARQL Engine - " + engine;
  // Populate knowledge base
  tab1Content.querySelector(".card-title").innerHTML = "Knowledge Graph - " + kb;

  const tabBody = modalNode.querySelector("#queryList");
  const queryResult = performanceDataPerKb[kb][engine]["queries"];

  if (
    queryResult &&
    queryResult[0].runtime_info.hasOwnProperty("query_execution_tree") &&
    !execTreeEngines.includes(engine)
  ) {
    execTreeEngines.push(engine);
  }

  document.getElementById("resultsTable").replaceChildren();

  for (let id of ["#tab2Content", "#tab3Content", "#tab4Content"]) {
    const tabContent = modalNode.querySelector(id);
    tabContent.replaceChildren(document.createTextNode("Please select a query from the table in Query runtimes tab"));
  }
  document.getElementById("result-tree").replaceChildren();

  createQueryTable(queryResult, tabBody);
  $("#runtimes-tab-pane table").tablesorter({
    theme: "bootstrap",
    sortStable: true,
    sortInitialOrder: "desc",
  });

  document.querySelector("#queryDetailsModal").querySelector(".modal-footer").classList.add("d-none");
  const { q, t } = fixUrlAndState(queryResult.length, selectedQuery, tabToOpen);
  if (q !== null) {
    document.querySelector("#queryList").querySelectorAll("tr")[q].classList.add("table-active");
    populateTabsFromSelectedRow(queryResult[q]);
  }
  if (t !== null) {
    showTab(t);
  }
  hideSpinner();
}

/**
 * Creates and populates the query table inside the modal with query results and runtimes.
 *
 * - Iterates over the query results and dynamically creates table rows.
 * - Each row displays the query and its runtime, along with click event listeners.
 *
 * @param {Object[]} queryResult - The array of query result objects.
 * @param {string} kb - The name of the knowledge base.
 * @param {string} engine - The SPARQL engine used.
 * @param {HTMLElement} tabBody - The #queryList element.
 */
function createQueryTable(queryResult, tabBody) {
  queryResult.forEach((query, i) => {
    const tabRow = document.createElement("tr");
    tabRow.style.cursor = "pointer";
    tabRow.addEventListener("click", handleTabRowClick.bind(null, query));
    let runtime;
    if (query.runtime_info && Object.hasOwn(query.runtime_info, "client_time")) {
      runtime = formatNumber(query.runtime_info.client_time);
    } else {
      runtime = "N/A";
    }

    const actualSize = query.result_size ? query.result_size : 0;
    const resultSizeClass = !document.querySelector("#showResultSizeQd").checked ? "d-none" : "";
    let resultSizeText = format(actualSize);
    if (actualSize === 1 && query.headers.length === 1 && Array.isArray(query.results) && query.results.length == 1) {
      const resultValue = Array.isArray(query.results[0]) ? query.results[0][0] : query.results[0];
      let singleResult = extractCoreValue(resultValue);
      singleResult = parseInt(singleResult) ? format(singleResult) : singleResult;
      resultSizeText = `1 [${singleResult}]`;
    }
    const resultSizeLine = `<div class="text-muted small ${resultSizeClass}">${resultSizeText}</div>`;
    const cellInnerHTML = `
      ${runtime}
      ${resultSizeLine}
    `;
    
    const failed = query.headers.length === 0 || !Array.isArray(query.results);
    const failedTitle = failed ? EscapeAttribute(query.results) : "";

    resultClass = query.headers.length === 0 || !Array.isArray(query.results) ? "bg-danger bg-opacity-25" : "";
    tabRow.innerHTML = `
            <td title="${EscapeAttribute(query.sparql)}">${query.query}</td>
            <td class="text-end ${resultClass}" title="${failedTitle}">${cellInnerHTML}</td>
        `;
    tabBody.appendChild(tabRow);
  });
}

/**
 * Handles the click event on a query row within the query table.
 *
 * - Highlights the selected row and switches to the query details tab.
 * - Generates the query SPARQL, execution results, and execution tree in their relevant tabs
 *
 * @param {Object} queryRow - The object representing the query details.
 * @param {Event} event - The click event triggered by selecting a query row.
 */
function handleTabRowClick(queryRow, event) {
  const kb = document.querySelector("#queryDetailsModal").getAttribute("data-kb");
  const engine = document.querySelector("#queryDetailsModal").getAttribute("data-engine");
  updateUrlAndState(kb, engine, event.currentTarget.rowIndex - 1, 1);
  let activeRow = document.querySelector("#queryList").querySelector(".table-active");
  if (activeRow) {
    if (activeRow.rowIndex === event.currentTarget.rowIndex) {
      showTab(1);
      return;
    }
    activeRow.classList.remove("table-active");
  }
  event.currentTarget.classList.add("table-active");
  showSpinner();
  showTab(1);
  populateTabsFromSelectedRow(queryRow);
  hideSpinner();
}

/**
 * - Generates the query SPARQL, execution results, and execution tree in their relevant tabs
 *
 * @param {Object} queryRow - The object representing the query details.
 */
function populateTabsFromSelectedRow(queryRow) {
  const tab2Content = document.querySelector("#tab2Content");
  tab2Content.textContent = queryRow.sparql;
  document.querySelector("#showMore").classList.replace("d-flex", "d-none");
  const showMoreCloneButton = document.querySelector("#showMoreButton").cloneNode(true);
  document.querySelector("#showMore").replaceChild(showMoreCloneButton, document.querySelector("#showMoreButton"));
  generateHTMLTable(queryRow);
  generateExecutionTree(queryRow);
}

/**
 * - Display the tab corresponding to the passed tabIndex
 *
 * @param {number} tabIndex - index of the tab to display (0 - 3)
 */
function showTab(tabIndex) {
  const tabNodeId = document.querySelectorAll("#myTab button")[tabIndex].id;
  const tab = bootstrap.Tab.getOrCreateInstance(document.getElementById(tabNodeId));
  tab.show();
  // Enable zoom buttons for execution tree tab (2)
  if (tabIndex === 2 && document.querySelector("#result-tree").children.length !== 0) {
    document.querySelector("#queryDetailsModal").querySelector(".modal-footer").classList.remove("d-none");
  }
}

/**
 * Generates the query results table for a set of results.
 *
 * - Iterates over the provided results and creates table rows for each result entry.
 * - Handles formatting of SPARQL results, stripping unnecessary data type information.
 *
 * @param {string[][]} results - A 2D array representing the query results.
 */
function generateQueryResultsTable(results, headers) {
  const table = document.getElementById("resultsTable");
  const tableFragment = document.createDocumentFragment();

  if (headers) {
    const headerRow = document.createElement("tr");
    for (const header of headers) {
      const headerCell = document.createElement("th");
      headerCell.textContent = header;
      headerRow.appendChild(headerCell);
    }
    tableFragment.appendChild(headerRow);
  }

  const index = results.length > 1000 ? 1000 : results.length;
  // Create table rows
  for (let i = 0; i < index; i++) {
    const row = document.createElement("tr");
    for (let j = 0; j < results[i].length; j++) {
      const cell = document.createElement("td");

      // Extract only the value without the data type information
      let value = results[i][j];
      if (!value) value = "N/A";
      else if (value.startsWith('"') && value.endsWith('"')) {
        value = value.slice(1, -1); // Remove double quotes
      } else if (value.includes("^^<")) {
        value = value.split("^^<")[0]; // Remove data type
      }

      cell.textContent = value;
      row.appendChild(cell);
    }
    tableFragment.appendChild(row);
  }
  // Append the fragment to the table
  table.appendChild(tableFragment);
}

/**
 * Displays additional query results if there are more than 1000 results.
 *
 * - Handles pagination of results when there are more than 1000 entries.
 * - Dynamically loads more results when the "Show More" button is clicked.
 *
 * @param {string[][]} results - A 2D array representing the remaining query results.
 */
function displayMoreResults(results) {
  if (results.length > 1000) {
    generateQueryResultsTable(results.slice(0, 1000));
    let remainingResults = results.slice(1000);
    document.querySelector("#showMoreButton").addEventListener(
      "click",
      function () {
        displayMoreResults(remainingResults);
      },
      { once: true }
    );
  } else {
    generateQueryResultsTable(results);
    document.querySelector("#showMore").classList.replace("d-flex", "d-none");
  }
}

/**
 * Generates the HTML table for SPARQL query results and handles pagination if needed.
 *
 * - Displays a message if no results are available or if the query failed.
 * - Generates the query results table and manages the "Show More" button for large result sets.
 *
 * @param {string[][] | Object} tableData - A 2D array of query results or an error message object.
 */
function generateHTMLTable(queryRow) {
  const tableData = queryRow.results;
  const headers = queryRow.headers;
  document.getElementById("resultsTable").replaceChildren();
  if (!tableData) {
    document
      .getElementById("tab4Content")
      .replaceChildren(document.createTextNode("No SPARQL results available for this query!"));
    return;
  }
  if (!Array.isArray(tableData)) {
    document.getElementById("tab4Content").replaceChildren(document.createTextNode(tableData));
    return;
  }
  document.getElementById("tab4Content").replaceChildren();
  document.getElementById("resultsTable").replaceChildren();
  const h5Text = document.createElement("h5");
  const totalResults = queryRow.result_size;
  const resultsShown = totalResults <= 50 ? totalResults : 50;
  h5Text.textContent = `${
    queryRow.result_size
  } result(s) found for this query in ${queryRow.runtime_info.client_time.toPrecision(
    2
  )}s. Showing ${resultsShown} result(s)`;
  document.getElementById("tab4Content").replaceChildren(h5Text);
  generateQueryResultsTable(tableData, headers);
  if (1000 < tableData.length) {
    document.querySelector("#showMore").classList.replace("d-none", "d-flex");
    let remainingResults = tableData.slice(1000);
    document.querySelector("#showMoreButton").addEventListener(
      "click",
      function displayResults() {
        displayMoreResults(remainingResults);
      },
      { once: true }
    );
  }
}
