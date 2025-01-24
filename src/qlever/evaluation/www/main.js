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
            <td class="text-center">${engine}</td>
            <td class="text-end" style="padding-right:2rem">${engineData.failed}%</td>
            <td class="text-end" style="padding-right:2rem">${
              formatNumber(parseFloat(engineData.avgTime))
            }</td>
            <td class="text-end" style="padding-right:2rem">${
              formatNumber(parseFloat(engineData.medianTime))
            }</td>
            <td class="text-end" style="padding-right:2rem">${
              formatNumber(parseFloat(engineData.under1s))
            }</td>
            <td class="text-end" style="padding-right:2rem">${
              formatNumber(parseFloat(engineData.between1to5s)) + "%"
            }</td>
            <td class="text-end" style="padding-right:2rem">${
              formatNumber(parseFloat(engineData.over5s)) + "%"
            }</td>
        `;
    cardBody.appendChild(row);
  });
  return clone;
}

/**
 * Get urls for all the eval(tsv) and fail(txt) data
 * @param  fileList Array of file names in the output directory
 * @return Array of eval and fail logs for each kb and engine combination
 */
function getFileUrls(fileList) {
  const fileUrls = [];
  const kb_engine_map = {};

  for (let file of fileList) {
    const parts = file.split(".");
    if (parts.length === 5 && parts[2] === "queries") {
      const kb = parts[0];
      const engine = parts[1];

      if (!kb_engine_map[kb]) {
        kb_engine_map[kb] = [];
      }

      if (!kb_engine_map[kb].includes(engine)) {
        kb_engine_map[kb].push(engine);
      }
    }
  }

  for (let kb of kbs) {
    performanceDataPerKb[kb.toLowerCase()] = {};
    for (let engine of sparqlEngines) {
      if (kb_engine_map[kb].includes(engine)) {
        const evalLog = getEvalLog(engine.toLowerCase(), kb.toLowerCase());
        const failLog = getFailLog(engine.toLowerCase(), kb.toLowerCase());
        fileUrls.push(evalLog);
        fileUrls.push(failLog);
      }
    }
  }
  return fileUrls;
}

/**
 * Create promises out of eval and fail logs and return the results
 * @param  fileUrls fileUrls array from getFileUrls function
 * @return Promise that is reolved with array of results of fetching eval and fail logs
 * @async
 */
async function fetchAndProcessFiles(fileUrls) {
  const fetchPromises = fileUrls.map(async (url) => {
    try {
      //const content = await response.text();
      const content = await getYamlData(url, {
        headers: {
          "Cache-Control": "no-cache",
        },
      });
      if (content == null) {
        throw new Error(`Failed to fetch ${url}`);
      }
      console.log(`File ${url} content: ${content}`);
      // Process the content as needed
      return { status: "fulfilled", value: content };
    } catch (error) {
      console.error(`Error fetching ${url}: ${error.message}`);
      // Handle the error gracefully
      return { status: "rejected", reason: error.message };
    }
  });

  const results = await Promise.allSettled(fetchPromises);
  return results; // Return the results to be accessed later
}

/**
 * Fetch all the relevant metrics required by populateCard function
 * @param  results      Array withresults from fetching yaml file
 * @param  fileList     fileList array from getOutputFiles function
 */
function processResults(results, fileList) {
  for (let i = 0; i < results.length; i++) {
    let fileNameComponents = fileList[i].split(".");
    const kb = fileNameComponents[0];
    const engine = fileNameComponents[1];
    if (results[i].status == "fulfilled" && results[i].value.status == "fulfilled") {
      const queryData = results[i].value.value;
      addQueryStatistics(queryData);
      performanceDataPerKb[kb][engine] = queryData;
    }
  }
}

/**
 * Populate global sparqlEngines and kbs array based on files in the output directory
 * @param  url url of the output directory
 * @async
 */
async function getOutputFiles(url) {
  try {
    const response = await fetch(url);
    const data = await response.text();

    // Parse the HTML response to extract file names
    const parser = new DOMParser();
    const htmlDoc = parser.parseFromString(data, "text/html");
    const fileList = Array.from(htmlDoc.querySelectorAll("a")).map((link) => link.textContent.trim());
    for (const file of fileList) {
      const parts = file.split(".");
      if (parts.length === 4 && parts[2] === "results") {
        const kb = parts[0];
        if (!kbs.includes(kb)) kbs.push(kb);
        const engine = parts[1];
        if (!sparqlEngines.includes(engine)) sparqlEngines.push(engine);
      }
    }
    return fileList;
  } catch (error) {
    console.error("Error fetching file list:", error);
  }
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

// Use the DOMContentLoaded event listener to ensure the DOM is ready
document.addEventListener("DOMContentLoaded", async function () {
  getOutputFiles(outputUrl).then(async function (fileList) {
    // Fetch the card template
    const response = await fetch("card-template.html");
    const templateText = await response.text();

    // Create a virtual DOM element to hold the template
    const tempDiv = document.createElement("div");
    tempDiv.innerHTML = templateText;
    const cardTemplate = tempDiv.querySelector("#cardTemplate");

    const fragment = document.createDocumentFragment();

    for (let kb of kbs) {
      performanceDataPerKb[kb.toLowerCase()] = {};
    }

    // For all the tsv files in the output folder, create bootstrap card and display on main page
    fetchAndProcessFiles(fileList).then(async (results) => {
      processResults(results, fileList, fragment, cardTemplate);
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
    });

    // Setup event listeners for queryDetailsModal, comparisonModal and compareExecModal
    setListenersForQueriesTabs();
    setListenersForCompareExecModal();
    setListenersForEnginesComparison();
  });
});
