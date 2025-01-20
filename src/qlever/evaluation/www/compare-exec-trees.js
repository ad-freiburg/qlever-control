// Zoom settings
const baseTreeTextFontSize = 80;
const minimumZoomPercent = 30;
const maximumZoomPercent = 80;
const zoomChange = 10;

/**
 * Sets up event listeners for the execution tree comparison modal.
 * - Handles clicks on the "Compare Execution Trees" button to display the comparison modal.
 * - Ensures smooth reopening of the query comparison modal, scrolling to the last selected query.
 * - Listens for actions to display and zoom in/out of the execution trees.
 */
function setListenersForCompareExecModal() {
  // When the modal is hidden
  document.querySelector("#compareExecTreeModal").addEventListener("hidden.bs.modal", function () {
    // Don't execute any url or state based code when back/forward button clicked
    if (document.querySelector("#compareExecTreeModal").getAttribute("pop-triggered")) {
      document.querySelector("#compareExecTreeModal").removeAttribute("pop-triggered");
      return;
    }
    // Display query Comparison modal again and scroll automatically to the last selected query
    const kb = document.querySelector("#compareExecTreeModal").getAttribute("data-kb");
    document.querySelector("#comparisonModal").setAttribute("data-kb", kb);
    showModal(document.querySelector("#comparisonModal"));
  });

  // Event to create and draw 2 execution trees side-by-side for comparison
  document.querySelector("#compareExecTreeModal").addEventListener("shown.bs.modal", function () {
    handleCompareExecTrees("modalShow");
  });

  // Event to handle zoom in/out of execution trees
  document.querySelector("#compExecTreeTabContent").addEventListener("click", function (event) {
    if (event.target.tagName === "BUTTON") {
      const buttonId = event.target.id;
      const purpose = buttonId.slice(0, -1);
      const buttonClicked = document.querySelector("#" + buttonId);
      const tree = buttonClicked.parentNode.parentNode.nextElementSibling;
      const treeId = "#" + tree.id;
      const currentFontSize = tree.querySelector(".node[class*=font-size-]").className.match(/font-size-(\d+)/)[1];
      // Zoom in and out for both trees when sync option enabled
      if (document.getElementById("syncScrollCheck").checked) {
        for (let treeId of ["#tree1", "#tree2"]) {
          handleCompareExecTrees(purpose, treeId, Number.parseInt(currentFontSize));
        }
      } else {
        handleCompareExecTrees(purpose, treeId, Number.parseInt(currentFontSize));
      }
    }
  });

  // Events to handle drag and scroll horizontally on compareExecTrees page
  for (const treeDiv of ["#result-tree", "#tree1", "#tree2"]) {
    var isDragging = false;
    var initialX = 0;
    var initialY = 0;
    var currentTreeDiv = null;

    document.querySelector(treeDiv).addEventListener("mousedown", (e) => {
      currentTreeDiv = treeDiv;
      document.querySelector(currentTreeDiv).style.cursor = "grabbing";
      isDragging = true;
      initialX = e.clientX;
      initialY = e.clientY;
      e.preventDefault();
    });
    document.querySelector(treeDiv).addEventListener("mousemove", (e) => {
      if (isDragging) {
        const deltaX = e.clientX - initialX;
        const deltaY = e.clientY - initialY;
        document.querySelector(currentTreeDiv).scrollLeft -= deltaX;
        document.querySelector(currentTreeDiv).scrollTop -= deltaY;
        if (document.getElementById("syncScrollCheck").checked && treeDiv !== "#result-tree") {
          syncScroll(currentTreeDiv);
        }
        initialX = e.clientX;
        initialY = e.clientY;
      }
    });
    // Sync scrolling and zooming if the option is selected
    document.querySelector(treeDiv).addEventListener("scroll", () => {
      if (document.getElementById("syncScrollCheck").checked && treeDiv !== "#result-tree") {
        syncScroll(treeDiv);
      }
    });
    document.addEventListener("mouseup", () => {
      isDragging = false;
      if (document.querySelector(currentTreeDiv)) document.querySelector(currentTreeDiv).style.cursor = "grab";
      currentTreeDiv = null;
    });
  }
}

/**
 * Synchronize the scrolling between the 2 compare exec trees if enabled
 * @param {string} sourceTree - ID of the tree where the scroll is performed. Can be #tree1 or #tree2
 */
function syncScroll(sourceTree) {
  const sourceDiv = document.querySelector(sourceTree);

  for (const targetTree of ["#tree1", "#tree2"]) {
    if (targetTree !== sourceTree) {
      const targetDiv = document.querySelector(targetTree);

      // Match scroll position
      targetDiv.scrollLeft = sourceDiv.scrollLeft;
      targetDiv.scrollTop = sourceDiv.scrollTop;
    }
  }
}

/**
 * Updates the url with kb and pushes the page to history stack
 * Calls the function to display the execution trees for comparison, with options to zoom in, zoom out, or reset zoom.
 * @param {string} purpose - Purpose of the display (e.g., "modalShow", "zoomIn", "zoomOut").
 * @param {string} idOfTreeToZoom - ID of the tree element to zoom in/out.
 * @param {number} currentFontSize - Current font size of the tree nodes.
 */
async function handleCompareExecTrees(purpose, idOfTreeToZoom, currentFontSize) {
  const modalNode = document.querySelector("#compareExecTreeModal");
  const select1 = modalNode.getAttribute("data-s1");
  const select2 = modalNode.getAttribute("data-s2");
  const kb = modalNode.getAttribute("data-kb");
  const queryIndex = Number.parseInt(modalNode.getAttribute("data-qid"));
  // Only when modal is shown and not when zoom buttons clicked
  if (purpose === "modalShow") {
    // If back/forward button, do nothing
    if (modalNode.getAttribute("pop-triggered")) {
      modalNode.removeAttribute("pop-triggered");
    }
    // Else Update the url params and push the page to history stack
    else {
      const url = new URL(window.location);
      url.searchParams.set("page", "compareExecTrees");
      url.searchParams.set("kb", kb);
      url.searchParams.set("s1", select1);
      url.searchParams.set("s2", select2);
      url.searchParams.set("qid", queryIndex);

      const state = { page: "compareExecTrees", kb: kb, s1: select1, s2: select2, qid: queryIndex };
      // If this page is directly opened from url, replace the null state in history stack
      if (window.history.state === null) {
        window.history.replaceState(state, "", url);
      } else {
        window.history.pushState(state, "", url);
      }
    }
  }
  showCompareExecTrees(purpose, select1, select2, kb, queryIndex, idOfTreeToZoom, currentFontSize);
}

/**
 * Display the execution trees for comparison, with options to zoom in, zoom out, or reset zoom.
 * @param {string} select1 - qlever engine version selected in first dropdown
 * @param {string} select2 - qlever engine version selected in second dropdown
 * @param {string} kb - selected Knowledge Base
 * @param {number} queryIndex - array index of the selected query
 * @param {string} purpose - Purpose of the display (e.g., "modalShow", "zoomIn", "zoomOut").
 * @param {string} idOfTreeToZoom - ID of the tree element to zoom in/out.
 * @param {number} currentFontSize - Current font size of the tree nodes.
 */
function showCompareExecTrees(purpose, select1, select2, kb, queryIndex, idOfTreeToZoom, currentFontSize) {
  const qlevers = [select1, select2];
  divIds = ["#engineTree1", "#engineTree2"];
  if (purpose === "modalShow") {
    for (let i = 0; i < 2; i++) {
      document.querySelector(divIds[i]).innerHTML = qlevers[i];
    }
  }
  document.querySelector("#runtimeQuery").textContent =
    "Query: " + performanceDataPerKb[kb][qlevers[0].toLowerCase()][queryIndex]["Query ID"];
  document.querySelector("#runtimeQuery").title =
    performanceDataPerKb[kb][qlevers[0].toLowerCase()][queryIndex]["Query"];
  qlevers.forEach((engine, index) => {
    let runtime = performanceDataPerKb[kb][engine.toLowerCase()][queryIndex]["Runtime"].query_execution_tree;
    let treeid = "#tree" + (index + 1).toString();
    if (purpose === "modalShow" || idOfTreeToZoom === treeid) {
      document.querySelector(treeid).replaceChildren();
      let tree = createExecTree(runtime, treeid);
      drawExecTree(tree, treeid, purpose, currentFontSize);
    }
  });
}

/**
 * Calculates the depth of a tree structure, where depth is the longest path from the root to any leaf node.
 * @param {Object} obj - The tree node or root object.
 * @returns {number} - The depth of the tree.
 */
function calculateTreeDepth(obj) {
  // Base case: if the object has no children, return 1
  if (!obj.children || obj.children.length === 0) {
    return 1;
  }
  // Initialize maxDepth to track the maximum depth
  let maxDepth = 0;
  // Calculate depth for each child and find the maximum depth
  obj.children.forEach((child) => {
    const depth = calculateTreeDepth(child);
    maxDepth = Math.max(maxDepth, depth);
  });
  // Return maximum depth + 1 (to account for the current node)
  return maxDepth + 1;
}

/**
 * Determines the font size for a tree visualization based on its depth, ensuring text is appropriately sized.
 * @param {number} fontSize - The base font size.
 * @param {number} depth - The depth of the tree.
 * @returns {number} - The adjusted font size.
 */
function getFontSizeForDepth(fontSize, depth) {
  // If depth is greater than 4, reduce font size by 10 for each increment beyond 4
  if (depth > 4) {
    fontSize -= (depth - 4) * zoomChange;
  }
  // Ensure font size doesn't go below 30
  fontSize = Math.max(fontSize, minimumZoomPercent);
  return fontSize;
}

/**
 * Calculates the new font size for tree nodes based on the purpose (zoom in/out or modal show) and current size.
 * @param {Object} tree - The tree structure object.
 * @param {string} purpose - The purpose of font size adjustment (e.g., "modalShow", "zoomIn", "zoomOut").
 * @param {number} currentFontSize - The current font size of the tree nodes.
 * @returns {number} - The new font size.
 */
function getNewFontSizeForTree(tree, purpose, currentFontSize) {
  let treeDepth;
  let newFontSize = currentFontSize ? currentFontSize : maximumZoomPercent;
  if (purpose === "modalShow") {
    treeDepth = calculateTreeDepth(tree.nodeStructure);
    newFontSize = getFontSizeForDepth(baseTreeTextFontSize, treeDepth);
  } else if (purpose === "zoomIn" && currentFontSize < maximumZoomPercent) {
    newFontSize += zoomChange;
  } else if (purpose === "zoomOut" && currentFontSize > minimumZoomPercent) {
    newFontSize -= zoomChange;
  }
  return newFontSize;
}

/**
 * Generates an execution tree structure for visualization based on the runtime information.
 * @param {Object} runtime - The runtime information containing the tree structure.
 * @param {string} treeid - The ID of the HTML element where the tree will be rendered.
 * @returns {Object} The tree structure ready for rendering with Treant.js.
 */
function createExecTree(runtime, treeid) {
  try {
    runtimeInfoForTreant(runtime);
    let tree = treeid;
    let treant_compare_tree = {
      chart: {
        container: tree,
        rootOrientation: "NORTH",
        connectors: { type: "step" },
        node: { HTMLclass: "font-size-" + maximumZoomPercent },
      },
      nodeStructure: runtime,
    };
    return treant_compare_tree;
  } catch (error) {
    console.error("CreateExecTree error: ", error);
    return {};
  }
}

/**
 * Draws the execution tree in the specified HTML container, applying zoom settings and highlighting nodes based on performance.
 *
 * @param {Object} treant_tree - The tree structure generated by Treant.js.
 * @param {string} treeid - The ID of the HTML container where the tree is displayed.
 * @param {string} purpose - The reason for drawing the tree ('modalShow', 'zoomIn', 'zoomOut').
 * @param {number} [currentFontSize] - The current font size of the tree nodes (optional).
 */
function drawExecTree(treant_tree, treeid, purpose, currentFontSize) {
  if (treant_tree && Object.keys(treant_tree).length !== 0) {
    const newFontSize = getNewFontSizeForTree(treant_tree, purpose, currentFontSize);
    treant_tree.chart.node.HTMLclass = "font-size-" + newFontSize.toString();
    new Treant(treant_tree);
    // Highlight node with high query times: cached -> yellow or light yellow, not
    // cached -> red or light red. Also grey out cached nodes.
    $("p.node-time")
      .filter(function () {
        return $(this).html() >= high_query_time_ms;
      })
      .parent()
      .addClass("high");
    $("p.node-time")
      .filter(function () {
        return $(this).html() >= very_high_query_time_ms;
      })
      .parent()
      .addClass("veryhigh");
    $("p.node-cached")
      .filter(function () {
        return $(this).html() == "true";
      })
      .parent()
      .addClass("cached");
    document.querySelector(treeid).lastChild.scrollIntoView({ block: "nearest", inline: "center" });
  }
}

/**
 * Transforms runtime information into a format compatible with Treant.js for creating hierarchical execution trees.
 * Propagates cached status through the tree nodes.
 *
 * @param {Object} runtime_info - The runtime information containing the query execution tree details.
 * @param {boolean} [parent_cached=false] - Whether the parent node was cached (used to propagate caching status).
 */
function runtimeInfoForTreant(runtime_info, parent_cached = false) {
  // Create text child with the information we want to see in the tree.
  if (runtime_info["text"] == undefined) {
    var text = {};
    if (runtime_info["column_names"] == undefined) {
      runtime_info["column_names"] = ["not yet available"];
    }
    text["name"] = runtime_info["description"]
      .replace(/<.*[#\/\.](.*)>/, "<$1>")
      .replace(/qlc_/g, "")
      .replace(/\?[A-Z_]*/g, function (match) {
        return match.toLowerCase();
      })
      .replace(/([a-z])([A-Z])/g, "$1-$2")
      .replace(/^([a-zA-Z-])*/, function (match) {
        return match.toUpperCase();
      })
      .replace(/([A-Z])-([A-Z])/g, "$1 $2")
      .replace(/AVAILABLE /, "")
      .replace(/a all/, "all");
    text["size"] = format(runtime_info["result_rows"]) + " x " + format(runtime_info["result_cols"]);
    text["cols"] = runtime_info["column_names"]
      .join(", ")
      .replace(/qlc_/g, "")
      .replace(/\?[A-Z_]*/g, function (match) {
        return match.toLowerCase();
      });
    text["time"] = runtime_info["was_cached"]
      ? runtime_info["details"]["original_operation_time"]
      : runtime_info["operation_time"];
    text["total"] = text["time"];
    text["cached"] = parent_cached == true ? true : runtime_info["was_cached"];
    if (typeof text["cached"] != "boolean") {
      text["cached"] = false;
    }
    // Save the original was_cached flag, before it's deleted, for use below.
    for (var key in runtime_info) {
      if (key != "children") {
        delete runtime_info[key];
      }
    }
    runtime_info["text"] = text;
    runtime_info["stackChildren"] = true;

    // Recurse over all children, propagating the was_cached flag from the
    // original runtime_info to all nodes in the subtree.
    runtime_info["children"].map((child) => runtimeInfoForTreant(child, text["cached"]));
    // If result is cached, subtract time from children, to get the original
    // operation time (instead of the original time for the whole subtree).
    if (text["cached"]) {
      runtime_info["children"].forEach(function (child) {
        // text["time"] -= child["text"]["total"];
      });
    }
  }
}

/**
 * Generates and displays the execution tree for a given query or retrieves it based on the selected engine and knowledge base.
 * Handles rendering the tree in the modal's content.
 *
 * @param {Object} queryRow - The selected query's runtime information.
 * @param {string} [purpose] - The reason for generating the tree ('modalShow', 'zoomIn', 'zoomOut').
 * @param {string} [treeid] - The ID of the tree container (optional).
 * @param {number} [currentFontSize] - The current font size of the tree nodes (optional).
 */
function generateExecutionTree(queryRow, purpose, treeid, currentFontSize) {
  if (queryRow === null && purpose !== undefined) {
    const kb = document
      .querySelector("#queryDetailsModal")
      .querySelector("#runtimes-tab-pane")
      .querySelector(".card-title")
      .textContent.substring("Knowledge Graph - ".length)
      .toLowerCase();
    const engine = document
      .querySelector("#queryDetailsModal")
      .querySelector(".modal-title")
      .textContent.substring("SPARQL Engine - ".length)
      .toLowerCase();
    const queryIndex = document.querySelector("#queryList").querySelector(".table-active").rowIndex - 1;
    let runtime = performanceDataPerKb[kb][engine][queryIndex]["Runtime"].query_execution_tree;
    document.querySelector(treeid).replaceChildren();
    let tree = createExecTree(runtime, treeid);
    drawExecTree(tree, treeid, purpose, currentFontSize);
    return;
  }
  if (!queryRow.runtime_info || !Object.hasOwn(queryRow.runtime_info, "query_execution_tree")) {
    document.getElementById("tab3Content").replaceChildren();
    document.getElementById("result-tree").replaceChildren();
    if (queryRow.result) {
      document
        .querySelector("#tab3Content")
        .replaceChildren(document.createTextNode("Execution tree not available for this engine!"));
    } else {
      document
        .querySelector("#tab3Content")
        .replaceChildren(document.createTextNode("No SPARQL results available for this query!"));
    }
    return;
  }
  document.getElementById("tab3Content").replaceChildren();
  document.getElementById("result-tree").replaceChildren();
  const exec_tree_tab = document.querySelector("#exec-tree-tab");
  exec_tree_tab.addEventListener(
    "shown.bs.tab",
    function () {
      const runtime = queryRow.runtime_info.query_execution_tree;
      const treant_tree = createExecTree(runtime, "#result-tree");
      drawExecTree(treant_tree, "#result-tree", "modalShow");
    },
    { once: true }
  );
}
