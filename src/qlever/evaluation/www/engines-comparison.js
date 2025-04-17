/**
 * Sets event listeners for the Engines Comparison Modal
 *
 * - Listens for click events to hide selected queries, reset them or open CompareExecTrees Modal
 * - Selects the previously selected row again and scrolls to it when user comes back
 */
function setListenersForEnginesComparison() {
  // Event to display compareExecTree modal with Exec tree comparison for selected engines
  document.querySelector("#compareExecTrees").addEventListener("click", (event) => {
    event.preventDefault();
    compareExecutionTreesClicked();
  });

  const comparisonModal = document.querySelector("#comparisonModal");
  // Before the modal is shown, update the url and history Stack and remove the previous table
  comparisonModal.addEventListener("show.bs.modal", async function () {
    const kb = comparisonModal.getAttribute("data-kb");
    if (kb) {
      // If back/forward button, do nothing
      if (comparisonModal.getAttribute("pop-triggered")) {
        comparisonModal.removeAttribute("pop-triggered");
      }
      // Else Update the url params and push the page to history stack
      else {
        const url = new URL(window.location);
        url.search = "";
        console.log(url.searchParams);
        url.searchParams.set("page", "comparison");
        url.searchParams.set("kb", kb);
        const state = { page: "comparison", kb: kb };
        // If this page is directly opened from url, replace the null state in history stack
        if (window.history.state === null) {
          window.history.replaceState(state, "", url);
        } else {
          window.history.pushState(state, "", url);
        }
      }

      const tableContainer = document.getElementById("table-container");
      tableContainer.replaceChildren();
      document.querySelector("#comparisonKb").innerHTML = "";
    }
  });

  // After the modal is shown, populate the modal based on the selected kb
  comparisonModal.addEventListener("shown.bs.modal", async function () {
    const kb = comparisonModal.getAttribute("data-kb");
    if (kb) {
      openComparisonModal(kb);
    }
    const popoverTriggerList = [].slice.call(comparisonModal.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (el) {
      return new bootstrap.Popover(el);
    });

    const resultSizeCheckbox = document.querySelector("#showResultSize");

    if (!resultSizeCheckbox.hasEventListener) {
      resultSizeCheckbox.addEventListener("change", function () {
        const tdElements = comparisonModal.querySelectorAll("td");
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
    // Scroll to the previously selected row if user is coming back to this modal
    const activeRow = comparisonModal.querySelector(".table-active");
    if (activeRow) {
      activeRow.scrollIntoView({
        behavior: "auto",
        block: "center",
        inline: "center",
      });
    }
  });

  // Handle the modal's `hidden.bs.modal` event
  comparisonModal.addEventListener("hidden.bs.modal", function () {
    // Don't execute any url or state based code when back/forward button clicked
    if (comparisonModal.getAttribute("pop-triggered")) {
      comparisonModal.removeAttribute("pop-triggered");
      return;
    }
    // Case: Modal was hidden as a result of clicking on compare execution trees button
    if (comparisonModal.getAttribute("compare-exec-clicked")) {
      const modalNode = document.querySelector("#compareExecTreeModal");

      // Set kb, selected sparql engines and query attributes and show compareExecTreeModal
      const kb = comparisonModal.getAttribute("data-kb");
      const select1 = document.querySelector("#select1").value;
      const select2 = document.querySelector("#select2").value;
      const queryIndex = document.querySelector("#comparisonModal .table-active").rowIndex - 1;

      modalNode.setAttribute("data-kb", kb);
      modalNode.setAttribute("data-s1", select1);
      modalNode.setAttribute("data-s2", select2);
      modalNode.setAttribute("data-qid", queryIndex);

      comparisonModal.removeAttribute("compare-exec-clicked");
      showModal(document.querySelector("#compareExecTreeModal"));
    }
    // Case: Modal was closed as result of clicking on the close button
    else {
      // Navigate to the main page and update the url
      const url = new URL(window.location);
      url.searchParams.delete("page");
      url.searchParams.delete("kb");
      window.history.pushState({ page: "main" }, "", url);
    }
  });
}

/**
 * Displays the execution tree comparison modal for the selected query.
 * Alerts the user if no query is selected.
 */
function compareExecutionTreesClicked() {
  const activeRow = document.querySelector("#comparisonModal").querySelector(".table-active");
  if (!activeRow) {
    alert("Please select a query from the table!");
    return;
  }
  const kb = document.querySelector("#comparisonModal").getAttribute("data-kb");
  const select1 = document.querySelector("#select1").value;
  const select2 = document.querySelector("#select2").value;
  const queryIndex = document.querySelector("#comparisonModal .table-active").rowIndex - 1;
  if (
    !performanceDataPerKb[kb][select1.toLowerCase()]["queries"][queryIndex] ||
    !performanceDataPerKb[kb][select2.toLowerCase()]["queries"][queryIndex]
  ) {
    alert("Execution tree not available for this query for these engines!");
    return;
  }
  document.querySelector("#comparisonModal").setAttribute("compare-exec-clicked", true);
  const compareResultsmodal = bootstrap.Modal.getInstance(document.querySelector("#comparisonModal"));
  compareResultsmodal.hide();
}

/**
 * Handle event when compare results button is clicked on the main page
 * @param  kb    name of the knowledge base
 * Display the modal page where all the engine runtimes are compared against each other on a per query basis
 */
function handleCompareResultsClick(kb) {
  const enginesToDisplay = getEnginesToDisplay(kb);
  if (enginesToDisplay.length === 0) {
    alert("All engines are unselected from comparison! Choose at least one or ideally more for comparison!");
    return;
  }
  document.querySelector("#comparisonModal").setAttribute("data-kb", kb);
  showModal(document.querySelector("#comparisonModal"));
}

function getEnginesToDisplay(kb) {
  for (const cardBody of document.querySelectorAll(".card-body")) {
    const selectedKb = cardBody.querySelector("h5").innerHTML.toLowerCase();
    if (kb === selectedKb) {
      let enginesToShow = [];
      for (const row of cardBody.querySelectorAll("tbody tr")) {
        if (row.children[0].firstElementChild.checked) {
          enginesToShow.push(row.children[1].innerHTML.toLowerCase());
        }
      }
      return enginesToShow;
    }
  }
}

/**
 * - Updates the url with kb and pushes the page to history stack
 * - Fetches the query log and results based on the selected knowledge base (KB) and engine.
 * - Updates the modal content and displays the query details.
 * - Manages the state of the query execution tree and tab content.
 *
 * @async
 * @param {string} kb - The selected knowledge base
 */
function openComparisonModal(kb) {
  const enginesToDisplay = getEnginesToDisplay(kb);
  console.log(enginesToDisplay);

  showSpinner();
  document.querySelector("#comparisonKb").innerHTML = kb;
  const tableContainer = document.getElementById("table-container");
  // Populate the dropdowns with qlever engines for execution tree comparison
  let select1 = document.querySelector("#select1");
  let select2 = document.querySelector("#select2");
  select1.innerHTML = "";
  select2.innerHTML = "";
  for (let engine of enginesToDisplay) {
    //await addRuntimeToPerformanceDataPerKb(kb, engine);
    if (performanceDataPerKb[kb].hasOwnProperty(engine) && execTreeEngines.includes(engine)) {
      select1.add(new Option(engine));
      select2.add(new Option(engine));
    }
  }
  // If only 1 or less qlever engine, hide compare execution trees button
  if (select1.options.length <= 1) {
    document.querySelector("#compareExecDiv").classList.add("d-none");
  } else {
    document.querySelector("#compareExecDiv").classList.remove("d-none");
    // By default show the first and second options when 2 or more options available
    select1.selectedIndex = 0;
    select2.selectedIndex = 1;
  }

  // Create a DocumentFragment to build the table
  const fragment = document.createDocumentFragment();
  const table = createCompareResultsTable(kb, enginesToDisplay);

  fragment.appendChild(table);

  // Append the table to the container in a single operation
  tableContainer.appendChild(fragment);

  $("#table-container table").tablesorter({
    theme: "bootstrap",
    sortStable: true,
    sortInitialOrder: "desc",
  });
  hideSpinner();
}

function getBestRuntime(kb, engines, queryId) {
  best_time = Infinity;
  for (let engine of engines) {
    const result = performanceDataPerKb[kb][engine]["queries"][queryId];
    let runtime = parseFloat(result.runtime_info.client_time);
    let failed = result.headers.length === 0 || !Array.isArray(result.results);
    if (!failed && runtime < best_time) {
      best_time = runtime;
    }
  }
  return best_time;
}

function getMajorityResultSize(kb, engines, queryId) {
  const sizeCounts = new Map();
  let validResultFound = false;

  for (let engine of engines) {
    const result = performanceDataPerKb[kb][engine]["queries"][queryId];
    const failed = result.headers.length === 0 || !Array.isArray(result.results);

    if (!failed && typeof result.result_size === "number" && result.result_size !== 0) {
      validResultFound = true;
      const size = result.result_size;
      sizeCounts.set(size, (sizeCounts.get(size) || 0) + 1);
    }
  }

  if (!validResultFound || sizeCounts.size === 0) {
    // All results failed or only had result_size = 0
    return null;
  }

  let majorityResultSize = null;
  let maxCount = 0;

  for (const [size, count] of sizeCounts.entries()) {
    if (count > maxCount) {
      maxCount = count;
      majorityResultSize = size;
    }
  }

  return majorityResultSize;
}

/**
 * Uses performanceDataPerKb object to create the engine runtime for each query comparison table
 * Gives the user the ability to selectively hide queries to reduce the clutter
 * @param  kb Name of the knowledge base for which to get engine runtimes
 * @return HTML table with queries as rows and engine runtimes as columns
 */
function createCompareResultsTable(kb, enginesToDisplay) {
  let queryCount = 0;
  const table = document.createElement("table");
  table.classList.add("table", "table-hover", "table-bordered", "w-auto");

  // Create the table header row
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  headerRow.title = `
    Click on a column to sort it in descending or ascending order. 
    Sort multiple columns simultaneously by holding down the Shift key 
    and clicking a second, third or even fourth column header!
  `;

  // Create dynamic headers and add them to the header row
  headerRow.innerHTML = "<th class='sticky-top'>Query</th>";
  const engines = enginesToDisplay;
  let engineIndexForQueriesList = 0;
  for (let i = 0; i < engines.length; i++) {
    if (performanceDataPerKb[kb][engines[i]]["queries"].length > queryCount) {
      queryCount = performanceDataPerKb[kb][engines[i]]["queries"].length;
      engineIndexForQueriesList = i;
    }
    headerRow.innerHTML += `<th class='sticky-top'>${engines[i]}</th>`;
  }

  thead.appendChild(headerRow);
  table.appendChild(thead);

  // Create the table body and add rows and cells
  const tbody = document.createElement("tbody");
  for (let i = 0; i < queryCount; i++) {
    const row = document.createElement("tr");
    const title = EscapeAttribute(performanceDataPerKb[kb][engines[engineIndexForQueriesList]]["queries"][i]["sparql"]);
    row.innerHTML += `<td title="${title}">${
      performanceDataPerKb[kb][engines[engineIndexForQueriesList]]["queries"][i]["query"]
    }</td>`;
    const bestRuntime = getBestRuntime(kb, engines, i);
    const majorityResultSize = getMajorityResultSize(kb, engines, i);
    for (let engine of engines) {
      const result = performanceDataPerKb[kb][engine]["queries"][i];
      if (!result) {
        row.innerHTML += "<td class='text-end'>N/A</td>";
        continue;
      }
      let runtime = result.runtime_info.client_time;
      const failed = result.headers.length === 0 || !Array.isArray(result.results);
      let resultClass = failed ? "bg-danger bg-opacity-25" : "";
      if (resultClass === "" && runtime === bestRuntime) {
        resultClass = "bg-success bg-opacity-25";
      }
      let popoverContent = "";
      let warningSymbol = "";
      const actualSize = result.result_size ? result.result_size : 0;
      if (failed) {
        popoverContent = result.results;
      } else if (resultClass.includes("bg-success")) {
        popoverContent = "Best runtime for this query!";
      }
      if (majorityResultSize !== null && !failed && actualSize !== majorityResultSize) {
        warningSymbol = ` <span style="color:red">&#9888;</span>`;
        popoverContent +=
          (popoverContent ? " " : "") +
          `Warning: Result size (${format(actualSize)}) differs from majority (${format(majorityResultSize)}).`;
      }
      let runtimeText = `${formatNumber(parseFloat(runtime))} s${warningSymbol}`;
      let popoverTitle = null;
      const resultSizeClass = !document.querySelector("#showResultSize").checked ? "d-none" : "";
      let resultSizeText = format(actualSize);
      if (actualSize === 1 && result.headers.length === 1 && Array.isArray(result.results) && result.results.length == 1) {
        let singleResult = extractCoreValue(result.results[0]);
        singleResult = parseInt(singleResult) ? format(singleResult) : singleResult;
        resultSizeText = `1 [${singleResult}]`;
      }
      const resultSizeLine = `<div class="text-muted small ${resultSizeClass}">${resultSizeText}</div>`;
      const cellInnerHTML = `
        ${runtimeText}
        ${resultSizeLine}
      `;
      if (popoverTitle) {
        popoverContent = `<b>${EscapeAttribute(popoverTitle)}</b><br>${EscapeAttribute(popoverContent)}`
      }
      else {
        popoverContent = EscapeAttribute(popoverContent)
      }

      // row.innerHTML += `<td title="${popoverContent}" class="text-end ${resultClass}">${runtimeText}</td>`;
      row.innerHTML += `
        <td
          tabindex="0"
          class="text-end ${resultClass}"
          data-bs-toggle="popover"
          data-bs-trigger="hover focus"
          data-bs-html="true"
          data-bs-content="${popoverContent}"
        >
        ${cellInnerHTML}
        </td>
      `;
    }
    // title="${EscapeAttribute(popoverTitle)}"
    if (!document.querySelector("#compareExecDiv").classList.contains("d-none")) {
      row.style.cursor = "pointer";
      row.addEventListener("click", function () {
        let activeRow = document.querySelector("#comparisonModal").querySelector(".table-active");
        if (activeRow) activeRow.classList.remove("table-active");
        row.classList.add("table-active");
      });
    }
    tbody.appendChild(row);
  }
  table.appendChild(tbody);

  return table;
}
