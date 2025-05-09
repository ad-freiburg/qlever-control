/**
 * Create a bootstrap card with engine metrics from cardTemplate for the main page
 * @param  cardTemplate cardTemplate document node
 * @param  kb           name of the knowledge base
 * @param  data         metrics for each SPARQL engine for the given knowledge base
 * @return A bootstrap card displaying SPARQL Engine metrics for the given kb
 */
function populateCard(cardTemplate, kb) {
  const clone = document.importNode(cardTemplate.content, true);
  const cardTitle = clone.querySelector("h5");
  clone.querySelector("button").addEventListener("click", handleCompareResultsClick.bind(null, kb));
  cardTitle.innerHTML = kb[0].toUpperCase() + kb.slice(1);
  const cardBody = clone.querySelector("tbody");

  Object.keys(performanceDataPerKb[kb]).forEach((engine) => {
    const engineData = performanceDataPerKb[kb][engine];
    const row = document.createElement("tr");
    row.style.cursor = "pointer";
    row.addEventListener("click", handleRowClick);
    row.innerHTML = `
            <td class="text-center" title="Unselecting this will remove this engine from comparison table that shows on clicking the Compare Results Button">
              <input type="checkbox" class="form-check-input row-checkbox" checked>
            </td>
            <td class="text-center">${engine}</td>
            <td class="text-end" style="padding-right:2rem">${formatNumber(parseFloat(engineData.failed))}%</td>
            <td class="text-end" style="padding-right:2rem">${formatNumber(parseFloat(engineData.gmeanTime))}s</td>
            <td class="text-end" style="padding-right:2rem">${formatNumber(parseFloat(engineData.ameanTime))}s</td>
            <td class="text-end" style="padding-right:2rem">${formatNumber(parseFloat(engineData.medianTime))}s</td>
            <td class="text-end" style="padding-right:2rem">${formatNumber(parseFloat(engineData.under1s))}%</td>
            <td class="text-end" style="padding-right:2rem">${formatNumber(parseFloat(engineData.between1to5s))}%</td>
            <td class="text-end" style="padding-right:2rem">${formatNumber(parseFloat(engineData.over5s))}%</td>
        `;
    cardBody.appendChild(row);
    addEventListenersForCard(clone.querySelector("table"));
  });
  return clone;
}

function addEventListenersForCard(cardNode) {
  thead = cardNode.querySelector("thead");
  tbody = cardNode.querySelector("tbody");
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
    const headerCheckbox = thead.querySelector("input");
    const rowCheckboxes = tbody.querySelectorAll(".row-checkbox");
    const allChecked = Array.from(rowCheckboxes).every((checkbox) => checkbox.checked);
    headerCheckbox.checked = allChecked;
  });
}

/**
 * Hide a modal if it is currently open.
 * Adds a custom `pop-triggered` attribute to the modal so that modal.hide() doesn't execute any code after closing
 * @param {HTMLElement} modalNode - The DOM node representing the modal to be hidden.
 */
function hideModalIfOpened(modalNode) {
  if (modalNode.classList.contains("show")) {
    modalNode.setAttribute("pop-triggered", true);
    bootstrap.Modal.getInstance(modalNode).hide();
  }
}

/**
 * Handle browser's back button actions by displaying or hiding modals based on the current state.
 * Dynamically adjusts modal attributes and visibility depending on the `page` property in the `popstate` event's state.
 * @param {PopStateEvent} event - The popstate event triggered by browser navigation actions.
 */
window.addEventListener("popstate", function (event) {
  const comparisonModal = document.querySelector("#comparisonModal");
  const queryDetailsModal = document.querySelector("#queryDetailsModal");
  const compareExecTreesModal = document.querySelector("#compareExecTreeModal");

  const state = event.state || {};
  const { page, kb, engine, q, t, s1, s2, qid } = state;
  const { selectedQuery, tab } = getSanitizedQAndT(q, t);

  // Close all modals initially
  //[comparisonModal, queryDetailsModal, compareExecTreesModal].forEach(hideModalIfOpened);

  switch (page) {
    case "comparison":
      [queryDetailsModal, compareExecTreesModal].forEach(hideModalIfOpened);
      showModal(comparisonModal, { "data-kb": kb }, true);
      break;

    case "queriesDetails":
      [comparisonModal, compareExecTreesModal].forEach(hideModalIfOpened);
      if (queryDetailsModal.classList.contains("show")) {
        tab ? showTab(tab) : showTab(0);
      } else {
        showModal(
          queryDetailsModal,
          { "data-kb": kb, "data-engine": engine, "data-query": selectedQuery, "data-tab": tab },
          true
        );
      }
      break;

    case "compareExecTrees":
      [comparisonModal, queryDetailsModal].forEach(hideModalIfOpened);
      showModal(compareExecTreesModal, { "data-kb": kb, "data-s1": s1, "data-s2": s2, "data-qid": qid }, true);
      break;

    case "main":
    default:
      [comparisonModal, queryDetailsModal, compareExecTreesModal].forEach(hideModalIfOpened);
      // No action needed for the main page
      break;
  }
});

/**
 * Display appropriate modals based on URL parameters.
 * Reads URL query parameters to determine the `page` and associated attributes,
 * then displays the corresponding modal.
 * If no valid page parameter is found, the URL is reset to the main page.
 * @async
 */
async function showPageFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  const page = urlParams.get("page");
  const kb = urlParams.get("kb")?.toLowerCase();
  const { selectedQuery, tab } = getSanitizedQAndT(urlParams.get("q"), urlParams.get("t"));
  const queryDetailsModal = document.querySelector("#queryDetailsModal");
  const comparisonModal = document.querySelector("#comparisonModal");
  const compareExecTreesModal = document.querySelector("#compareExecTreeModal");

  switch (page) {
    case "comparison":
      showModal(comparisonModal, { "data-kb": kb });
      break;

    case "queriesDetails":
      showModal(queryDetailsModal, {
        "data-kb": kb,
        "data-engine": urlParams.get("engine")?.toLowerCase(),
        "data-query": selectedQuery,
        "data-tab": tab,
      });
      break;

    case "compareExecTrees":
      showModal(compareExecTreesModal, {
        "data-kb": kb,
        "data-s1": urlParams.get("s1")?.toLowerCase(),
        "data-s2": urlParams.get("s2")?.toLowerCase(),
        "data-qid": urlParams.get("qid"),
      });
      break;

    default:
      // Navigate back to the main page if no valid page parameter
      const url = new URL(window.location);
      url.search = "";
      window.history.replaceState({ page: "main" }, "", url);
      break;
  }
}

function getSanitizedQAndT(q, t) {
  let selectedQuery = parseInt(q);
  let tab = parseInt(t);

  if (isNaN(tab) || tab < 1 || tab > 3) {
    tab = "";
  }

  if (isNaN(selectedQuery) || selectedQuery < 0) {
    selectedQuery = "";
  }
  return { selectedQuery: selectedQuery, tab: tab };
}

function augmentPerformanceDataPerKb(performanceDataPerKb) {
  for (const engines of Object.values(performanceDataPerKb)) {
    for (const { queries } of Object.values(engines)) {
      for (const query of queries) {
        const failed = query.headers.length === 0 || !Array.isArray(query.results);
        let singleResult = null;
        if (
          query.result_size === 1 &&
          query.headers.length === 1 &&
          Array.isArray(query.results) &&
          query.results.length == 1
        ) {
          let resultValue;
          if (Array.isArray(query.results[0]) && query.results[0].length > 0) {
            resultValue = query.results[0][0];
          } else {
            resultValue = query.results[0];
          }
          singleResult = extractCoreValue(resultValue);
          singleResult = parseInt(singleResult) ? format(singleResult) : singleResult;
        }
        query.failed = failed;
        query.singleResult = singleResult;
        query.result_size = query.result_size ? query.result_size : 0;
      }
    }
  }
}

// Use the DOMContentLoaded event listener to ensure the DOM is ready
document.addEventListener("DOMContentLoaded", async function () {
  // Fetch the card template
  const response = await fetch("card-template.html");
  const templateText = await response.text();

  // Create a virtual DOM element to hold the template
  const tempDiv = document.createElement("div");
  tempDiv.innerHTML = templateText;
  const cardTemplate = tempDiv.querySelector("#cardTemplate");

  const fragment = document.createDocumentFragment();

  try {
    // Get the current URL without the part after the final `/` (and ignore a
    // `/` at the end)
    const yaml_path = window.location.origin +
      window.location.pathname.replace(/\/$/, "").replace(/\/[^/]*$/, "/");
    const response = await fetch(yaml_path + "yaml_data");
    // const response = await fetch("../yaml_data");
    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }
    performanceDataPerKb = await response.json();
    augmentPerformanceDataPerKb(performanceDataPerKb);
    for (const kb of Object.keys(performanceDataPerKb)) {
      fragment.appendChild(populateCard(cardTemplate, kb));
    }
    document.getElementById("cardsContainer").appendChild(fragment);
    $("#cardsContainer table").tablesorter({
      theme: "bootstrap",
      sortStable: true,
      sortInitialOrder: "desc",
    });
    // Navigate to the correct page (or modal) based on the url
    await showPageFromUrl();
  } catch (error) {
    console.error("Failed to fetch performance data:", error);
    return null;
  }

  // Setup event listeners for queryDetailsModal, comparisonModal and compareExecModal
  setListenersForQueriesTabs();
  setListenersForCompareExecModal();
  setListenersForEnginesComparison();
});
