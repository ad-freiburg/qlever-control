/**
 * Sets event listeners for the Engines Comparison Modal
 *
 * - Listens for click events to hide selected queries, reset them or open CompareExecTrees Modal
 * - Selects the previously selected row again and scrolls to it when user comes back
 */
function setListenersForEnginesComparison() {
  document.getElementById("hideSelectedButton").addEventListener("click", hideSelectedButtonClicked);
  document.getElementById("resetButton").addEventListener("click", resetButtonClicked);
  document.getElementById("comparisonModal").addEventListener("hide.bs.modal", comparisonModalHidden);

  // Event to display compareExecTree modal with Exec tree comparison for selected engines
  document.querySelector("#compareExecTrees").addEventListener("click", (event) => {
    event.preventDefault();
    compareExecutionTreesClicked();
  });

  // Before the modal is shown, update the url and history Stack and remove the previous table
  document.querySelector("#comparisonModal").addEventListener("show.bs.modal", async function () {
    const kb = document.querySelector("#comparisonModal").getAttribute("data-kb");
    if (kb) {
      // If back/forward button, do nothing
      if (document.querySelector("#comparisonModal").getAttribute("pop-triggered")) {
        document.querySelector("#comparisonModal").removeAttribute("pop-triggered");
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

      // Open the previously opened modal without any processing overhead if kb is the same
      if (document.querySelector("#comparisonKb").innerHTML === kb) {
        return;
      }
      // Else clear the table with queries and engines runtimes before the modal is shown
      else {
        const tableContainer = document.getElementById("table-container");
        tableContainer.replaceChildren();
        document.querySelector("#comparisonKb").innerHTML = "";
      }
    }
  });

  // After the modal is shown, populate the modal based on the selected kb
  document.querySelector("#comparisonModal").addEventListener("shown.bs.modal", async function () {
    const kb = document.querySelector("#comparisonModal").getAttribute("data-kb");
    if (kb) {
      openComparisonModal(kb);
    }
    // Scroll to the previously selected row if user is coming back to this modal
    const activeRow = document.querySelector("#comparisonModal").querySelector(".table-active");
    if (activeRow) {
      activeRow.scrollIntoView({
        behavior: "auto",
        block: "center",
        inline: "center",
      });
    }
  });

  // Handle the modal's `hidden.bs.modal` event
  document.querySelector("#comparisonModal").addEventListener("hidden.bs.modal", function () {
    // Don't execute any url or state based code when back/forward button clicked
    if (document.querySelector("#comparisonModal").getAttribute("pop-triggered")) {
      document.querySelector("#comparisonModal").removeAttribute("pop-triggered");
      return;
    }
    // Case: Modal was hidden as a result of clicking on compare execution trees button
    if (document.querySelector("#comparisonModal").getAttribute("compare-exec-clicked")) {
      const modalNode = document.querySelector("#compareExecTreeModal");

      // Set kb, selected sparql engines and query attributes and show compareExecTreeModal
      const kb = document.querySelector("#comparisonModal").getAttribute("data-kb");
      const select1 = document.querySelector("#select1").value;
      const select2 = document.querySelector("#select2").value;
      const queryIndex = document.querySelector("#comparisonModal .table-active").rowIndex - 1;

      modalNode.setAttribute("data-kb", kb);
      modalNode.setAttribute("data-s1", select1);
      modalNode.setAttribute("data-s2", select2);
      modalNode.setAttribute("data-qid", queryIndex);

      document.querySelector("#comparisonModal").removeAttribute("compare-exec-clicked");
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
  document.querySelector("#comparisonModal").setAttribute("data-kb", kb);
  showModal(document.querySelector("#comparisonModal"));
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
  // Open the previously opened modal without any processing overhead if kb is the same
  if (document.querySelector("#comparisonKb").innerHTML === kb) {
    return;
  }

  showSpinner();
  document.querySelector("#comparisonKb").innerHTML = kb;
  const tableContainer = document.getElementById("table-container");
  // Populate the dropdowns with qlever engines for execution tree comparison
  let select1 = document.querySelector("#select1");
  let select2 = document.querySelector("#select2");
  select1.innerHTML = "";
  select2.innerHTML = "";
  for (let engine of sparqlEngines) {
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

  // If there is a previously saved state for the runtimes comparison table, fetch that and show it.
  // Also re-attach the click event listener to all the rows that were lost when the table state was saved
  if (comparisonTables.hasOwnProperty(kb) && comparisonTables[kb]) {
    tableContainer.innerHTML = comparisonTables[kb];
    const rows = tableContainer.querySelectorAll("tbody tr");
    for (const row of rows) {
      row.addEventListener("click", function () {
        let activeRow = document.querySelector("#comparisonModal").querySelector(".table-active");
        if (activeRow) activeRow.classList.remove("table-active");
        row.classList.add("table-active");
      });
    }
  } else {
    // Create a DocumentFragment to build the table
    const fragment = document.createDocumentFragment();
    const table = createCompareResultsTable(kb);

    fragment.appendChild(table);

    // Append the table to the container in a single operation
    tableContainer.appendChild(fragment);
  }

  $("#table-container table").tablesorter({
    theme: "bootstrap",
    sortStable: true,
    sortInitialOrder: "desc",
  });
  hideSpinner();
}

/**
 * Uses performanceDataPerKb object to create the engine runtime for each query comparison table
 * Gives the user the ability to selectively hide queries to reduce the clutter
 * @param  kb Name of the knowledge base for which to get engine runtimes
 * @return HTML table with queries as rows and engine runtimes as columns
 */
function createCompareResultsTable(kb) {
  let queryCount = 0;
  const table = document.createElement("table");
  table.classList.add("table", "table-hover", "table-bordered", "w-auto");

  // Create the table header row
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  headerRow.title =
    "Click on a column to sort it in descending or ascending order. Sort multiple columns simultaneously by holding down the Shift key and clicking a second, third or even fourth column header!";

  headerRow.innerHTML = `
      <th title="Select/Unselect all queries below">
        <input id="selectAll" type="checkbox" class="form-check-input">
      </th>
    `;
  // Create dynamic headers and add them to the header row
  headerRow.innerHTML += "<th>Query</th>";
  const engines = Object.keys(performanceDataPerKb[kb]);
  let engineIndexForQueriesList = 0;
  for (let i = 0; i < engines.length; i++) {
    if (performanceDataPerKb[kb][engines[i]]["queries"].length > queryCount) {
      queryCount = performanceDataPerKb[kb][engines[i]]["queries"].length;
      engineIndexForQueriesList = i;
    }
    headerRow.innerHTML += `<th>${engines[i]}</th>`;
  }

  thead.appendChild(headerRow);
  table.appendChild(thead);

  // Create the table body and add rows and cells
  const tbody = document.createElement("tbody");
  for (let i = 0; i < queryCount; i++) {
    const row = document.createElement("tr");
    row.innerHTML = `
        <td title="Select and click on Hide selected button to hide this query">
          <input type="checkbox" class="form-check-input row-checkbox">
        </td>
      `;
    row.style.cursor = "pointer";
    const title = performanceDataPerKb[kb][engines[engineIndexForQueriesList]]["queries"][i]["sparql"];
    row.innerHTML += `<td title="${title}">${
      performanceDataPerKb[kb][engines[engineIndexForQueriesList]]["queries"][i]["query"]
    }</td>`;
    for (let engine of engines) {
      const result = performanceDataPerKb[kb][engine]["queries"][i];
      if (!result) {
        row.innerHTML += "<td class='text-end'>N/A</td>";
        continue;
      }
      let runtime = result.runtime_info.client_time;
      let resultClass = result.headers.length === 0 || !Array.isArray(result.results) ? "bg-danger bg-opacity-25" : "";
      let runtimeText = `${formatNumber(parseFloat(runtime))} s`;
      row.innerHTML += `<td  class="text-end ${resultClass}">${runtimeText}</td>`;
    }
    row.addEventListener("click", function () {
      let activeRow = document.querySelector("#comparisonModal").querySelector(".table-active");
      if (activeRow) activeRow.classList.remove("table-active");
      row.classList.add("table-active");
    });
    tbody.appendChild(row);
  }
  table.appendChild(tbody);

  // Add event listeners for header and row checkboxes

  // If the header is checked, all the rows must be checked and vice-versa
  thead.addEventListener("change", function (event) {
    const headerCheckbox = event.target;
    const rowCheckboxes = tbody.querySelectorAll(".row-checkbox");
    rowCheckboxes.forEach((checkbox) => {
      checkbox.checked = headerCheckbox.checked;
    });
  });

  // Update the checker status of header based on if all rows are selected or not
  tbody.addEventListener("change", function () {
    const headerCheckbox = thead.querySelector("#selectAll");
    const rowCheckboxes = tbody.querySelectorAll(".row-checkbox");
    const allChecked = Array.from(rowCheckboxes).every((checkbox) => checkbox.checked);
    const noneChecked = Array.from(rowCheckboxes).every((checkbox) => !checkbox.checked);
    headerCheckbox.checked = allChecked;
    headerCheckbox.indeterminate = !allChecked && !noneChecked;
  });

  return table;
}

/**
 * Hide rows in the table where checkboxes are selected.
 * Ensures the "select all" header checkbox is not checked and prevents hiding all rows.
 * Alerts the user if an attempt is made to hide all rows of the table.
 */
function hideSelectedButtonClicked() {
  const table = document.querySelector("#table-container table");
  const checkboxes = table.querySelectorAll("tbody .row-checkbox:checked"); // Selected checkboxes
  const headerCheckbox = table.querySelector("#selectAll"); // Header selectAll checkbox

  if (headerCheckbox.checked) {
    alert("Cannot hide all the rows of the table!");
    return;
  }

  // Hide rows with checked checkboxes
  checkboxes.forEach((checkbox) => {
    const row = checkbox.closest("tr");
    row.style.display = "none"; // Hide the row
    row.classList.remove("table-active");
  });

  headerCheckbox.checked = false;
  headerCheckbox.indeterminate = false;
}

/**
 * Reset the table to its default state.
 * Makes all rows visible, unchecks all checkboxes, and ensures the "select all" header checkbox is cleared.
 */
function resetButtonClicked() {
  const table = document.querySelector("#table-container table");
  const allRows = table.querySelectorAll("tbody tr");
  const allCheckboxes = table.querySelectorAll('input[type="checkbox"]');

  // Reset all rows to be visible
  allRows.forEach((row) => {
    row.style.display = ""; // Make the row visible
  });

  // Uncheck all checkboxes
  allCheckboxes.forEach((checkbox) => {
    checkbox.checked = false;
  });

  // Reset the header checkbox
  const headerCheckbox = table.querySelector("#selectAll");
  if (headerCheckbox) {
    headerCheckbox.checked = false;
    headerCheckbox.indeterminate = false;
  }
}

/**
 * Cache the HTML of the comparison table when the comparison modal is hidden.
 * Saves the table's current state in the `comparisonTables` object using the knowledge base (`kb`) as a key.
 */
function comparisonModalHidden() {
  const table = document.querySelector("#table-container table");
  const kb = document.querySelector("#comparisonKb").innerHTML;
  comparisonTables[kb] = table.outerHTML;
}
