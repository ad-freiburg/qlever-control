let detailsGridApi = null;

function setDetailsPageEvents() {
    // Adds functionality to buttons in the modal footer for zooming in/out the execution tree
    document.querySelector('[aria-label="Details zoom controls"]').addEventListener("click", function (event) {
        if (event.target.tagName === "BUTTON") {
            const purpose = event.target.id;
            const treeId = "#result-tree";
            const tree = document.querySelector(treeId);
            const currentFontSize = tree
                .querySelector(".node[class*=font-size-]")
                .className.match(/font-size-(\d+)/)[1];
            const kb = new URLSearchParams(window.location.hash.split("?")[1]).get("kb");
            const engine = new URLSearchParams(window.location.hash.split("?")[1]).get("engine");
            const selectedNodes = detailsGridApi.getSelectedNodes();
            if (selectedNodes.length === 1) {
                const queryIdx = detailsGridApi.getSelectedNodes()[0].rowIndex;
                const runtime_info = performanceData[kb][engine].queries[queryIdx].runtime_info;
                renderExecTree(runtime_info, "#result-tree", "#meta-info", purpose, Number.parseInt(currentFontSize));
            }
        }
    });
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
        sparql: [],
        runtime: [],
        failed: [],
        result_size: [],
    };

    for (const queryData of allQueriesData) {
        queryRuntimes.query.push(queryData.query);
        queryRuntimes.sparql.push(queryData.sparql);
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

class CustomDetailsTooltip {
    eGui;
    init(params) {
        const tooltipText = params.value || "";

        const container = document.createElement("div");
        container.className = "custom-tooltip";

        const textDiv = document.createElement("div");
        textDiv.className = "tooltip-text";
        textDiv.textContent = tooltipText;
        container.appendChild(textDiv);
        this.eGui = container;
    }

    getGui() {
        return this.eGui;
    }
}

/**
 * Returns column definitions for ag-Grid to display query runtime results.
 * Expected input data keys: query, runtime, failed, result_size.
 *
 * @returns {Array<Object>} columnDefs for ag-Grid
 */
function getQueryRuntimesColumnDefs() {
    return [
        {
            headerName: "SPARQL Query",
            field: "query",
            filter: "agTextColumnFilter",
            flex: 3,
            tooltipValueGetter: (params) => {
                return params.data.sparql;
            },
            tooltipComponent: CustomDetailsTooltip,
        },
        {
            headerName: "Runtime (s)",
            field: "runtime",
            type: "numericColumn",
            filter: "agNumberColumnFilter",
            flex: 1,
            valueFormatter: (params) => (params.value != null ? `${params.value.toFixed(2)}s` : ""),
        },
        {
            headerName: "Result Size",
            field: "result_size",
            type: "numericColumn",
            filter: "agTextColumnFilter",
            flex: 1.5,
        },
    ];
}

function setTabsToDefault() {
    document.querySelectorAll("#page-details .tab-pane").forEach((node) => {
        if (node.id === "runtimes-tab-pane") return;
        for (const div of node.querySelectorAll("div")) {
            if (div.classList.contains("alert-info")) div.classList.remove("d-none");
            else div.classList.add("d-none");
        }
    });
}

function renderExecTree(runtime_info, treeNodeId, metaNodeId, purpose = "showTree", currentFontSize) {
    // Show meta information (if it exists).
    const meta_info = runtime_info["meta"];

    const time_query_planning =
        "time_query_planning" in meta_info
            ? formatInteger(meta_info["time_query_planning"]) + " ms"
            : "[not available]";

    const time_index_scans_query_planning =
        "time_index_scans_query_planning" in meta_info
            ? formatInteger(meta_info["time_index_scans_query_planning"]) + " ms"
            : "[not available]";

    const total_time_computing =
        "total_time_computing" in meta_info ? formatInteger(meta_info["total_time_computing"]) + " ms" : "N/A";

        // Inject meta info into the DOM
    document.querySelector(metaNodeId).innerHTML = `<p>Time for query planning: ${time_query_planning}<br/>
    Time for index scans during query planning: ${time_index_scans_query_planning}<br/>
    Total time for computing the result: ${total_time_computing}</p>`;

    // Show the query execution tree (using Treant.js)
    addTextElementsToExecTreeForTreant(runtime_info["query_execution_tree"]);
    console.log(runtime_info.query_execution_tree);

    const treant_tree = {
        chart: {
            container: treeNodeId,
            rootOrientation: "NORTH",
            connectors: { type: "step" },
            node: { HTMLclass: "font-size-" + maximumZoomPercent },
        },
        nodeStructure: runtime_info["query_execution_tree"],
    };
    const newFontSize = getNewFontSizeForTree(treant_tree, purpose, currentFontSize);
    treant_tree.chart.node.HTMLclass = "font-size-" + newFontSize.toString();

    // Create new Treant tree
    new Treant(treant_tree);

    // Add tooltips with parsed .node-details info
    document.querySelectorAll("div.node").forEach(function (node) {
        const detailsChild = node.querySelector(".node-details");
        if (detailsChild) {
            const topPos = parseFloat(window.getComputedStyle(node).top);
            node.setAttribute("data-bs-toggle", "tooltip");
            node.setAttribute("data-bs-html", "true");
            node.setAttribute("data-bs-placement", topPos > 100 ? "top" : "bottom");

            let detailHTML = "";
            const details = JSON.parse(detailsChild.textContent);
            for (const key in details) {
                detailHTML += `<span>${key}: <strong>${details[key]}</strong></span><br>`;
            }

            node.setAttribute(
                "data-bs-title",
                `<div style="width: 250px">
                    <h6> Details </h6>
                    <div style="margin-top: 10px; margin-bottom: 10px;">
                    ${detailHTML}
                    </div>
                </div>`
            );

            // Manually initialize Bootstrap tooltip
            new bootstrap.Tooltip(node);
        }
    });

    // Highlight high/very high node-time values
    document.querySelectorAll("p.node-time").forEach(function (p) {
        const time = parseInt(p.textContent.replace(/,/g, ""));
        if (time >= window.high_query_time_ms) {
            p.parentElement.classList.add("high");
        }
        if (time >= window.very_high_query_time_ms) {
            p.parentElement.classList.add("veryhigh");
        }
    });

    // Add cache status classes
    document.querySelectorAll("p.node-cache-status").forEach(function (p) {
        const status = p.textContent;
        const parent = p.parentElement;

        if (status === "cached_not_pinned") {
            parent.classList.add("cached-not-pinned", "cached");
        } else if (status === "cached_pinned") {
            parent.classList.add("cached-pinned", "cached");
        } else if (status === "ancestor_cached") {
            parent.classList.add("ancestor-cached", "cached");
        }
    });

    // Add status classes
    document.querySelectorAll("p.node-status").forEach(function (p) {
        const status = p.textContent;
        const parent = p.parentElement;

        switch (status) {
            case "fully materialized":
                p.classList.add("fully-materialized");
                break;
            case "lazily materialized":
                p.classList.add("lazily-materialized");
                break;
            case "failed":
                p.classList.add("failed");
                break;
            case "failed because child failed":
                p.classList.add("child-failed");
                break;
            case "not yet started":
                parent.classList.add("not-started");
                break;
            case "optimized out":
                p.classList.add("optimized-out");
                break;
        }
    });

    // Add title for truncated node names and cols
    document.querySelectorAll("#result-tree p.node-name, #result-tree p.node-cols").forEach(function (p) {
        p.setAttribute("title", p.textContent);
    });
}

let exec_tree_listener = null;

function updateTabsWithSelectedRow(rowData) {
    console.log(rowData);
    const sparqlQuery = rowData?.sparql;
    if (sparqlQuery) {
        for (const div of document.querySelectorAll("#query-tab-pane div")) {
            if (div.classList.contains("alert-info")) div.classList.add("d-none");
            else div.classList.remove("d-none");
        }
        document.querySelector("#full-query").textContent = sparqlQuery;
    }

    const runtime_info = rowData?.runtime_info;
    if (runtime_info?.query_execution_tree) {
        for (const div of document.querySelectorAll("#exec-tree-tab-pane div")) {
            if (div.classList.contains("alert-info")) div.classList.add("d-none");
            else div.classList.remove("d-none");
        }
        document.querySelector("#result-tree").innerHTML = "";
        const exec_tree_tab = document.querySelector("#exec-tree-tab");
        if (exec_tree_listener) exec_tree_tab.removeEventListener("shown.bs.tab", exec_tree_listener);
        exec_tree_listener = () => {
            renderExecTree(runtime_info, "#result-tree", "#meta-info");
            exec_tree_listener = null;
        };
        exec_tree_tab.addEventListener("shown.bs.tab", exec_tree_listener, { once: true });
    } else {
        document.querySelector("#exec-tree-tab-pane div.alert-info").classList.add("d-none");
        document.querySelector("#result-tree-div").classList.remove("d-none");
        document.querySelector("#result-tree-div div.alert-info").classList.remove("d-none");
    }

    const headers = rowData?.headers;
    const queryResults = rowData?.results;
    for (const div of document.querySelectorAll("#results-tab-pane div")) {
        if (div.classList.contains("alert-info")) div.classList.add("d-none");
        else div.classList.remove("d-none");
    }
    const gridDiv = document.querySelector("#results-grid");
    gridDiv.innerHTML = "";
    if (Array.isArray(queryResults) && Array.isArray(headers)) {
        const textDiv = document.querySelector("#results-container div.alert");
        textDiv.classList.remove("alert-danger");
        textDiv.classList.add("alert-secondary");
        textDiv.innerHTML = `Showing ${rowData.results.length} results out of ${
            rowData?.result_size ?? 0
        } total results`;
        const rowCount = queryResults.length;
        const tableData = getQueryResultsDict(headers, queryResults);
        let domLayout = "normal";
        if (rowCount < 25) domLayout = "autoHeight";

        if (domLayout === "normal") {
            gridDiv.style.height = `${document.documentElement.clientHeight - 275}px`;
        }

        const gridData = getGridRowData(rowCount, tableData);
        const columnDefs = headers.map((key) => ({
            field: key,
            headerName: key,
        }));

        agGrid.createGrid(gridDiv, {
            columnDefs: columnDefs,
            rowData: gridData,
            defaultColDef: {
                sortable: true,
                filter: true,
                resizable: true,
                flex: 1,
                minWidth: 100,
            },
            domLayout: domLayout,
            rowStyle: { fontSize: "14px", cursor: "pointer" },
        });
    } else {
        const textDiv = document.querySelector("#results-container div.alert");
        textDiv.classList.add("alert-danger");
        textDiv.classList.remove("alert-secondary");
        textDiv.innerHTML = `Query failed in ${rowData.runtime_info.client_time.toFixed(2)} s with error: <br><br>${
            rowData.results
        }`;
    }
}

/**
 * Called when a row is selected in the runtime table
 */
function onRuntimeRowSelected(event, performanceData, kb, engine) {
    const selectedNode = event.api.getSelectedNodes();
    if (selectedNode.length === 1) {
        let selectedRowIdx = selectedNode[0].rowIndex;
        updateTabsWithSelectedRow(performanceData[kb][engine]["queries"][selectedRowIdx]);
        // router.navigate(`/details?kb=${encodeURIComponent(kb)}&engine=${encodeURIComponent(engine)}&q=${selectedRowIdx}`)
    } else {
        setTabsToDefault();
        // router.navigate(`/details?kb=${encodeURIComponent(kb)}&engine=${encodeURIComponent(engine)}&q=${selectedRowIdx}`)
    }
}

function updateDetailsPage(performanceData, kb, engine) {
    let engine_header = capitalize(engine);
    if (engine_header === "Qlever") engine_header = "QLever";
    const titleNode = document.querySelector("#details-title");
    if (titleNode.innerHTML === `Details - ${engine_header} (${capitalize(kb)})`) return;
    else titleNode.innerHTML = `Details - ${engine_header} (${capitalize(kb)})`;

    setTabsToDefault();
    const tab = new bootstrap.Tab(document.querySelector("#runtimes-tab"));
    tab.show();

    const tableData = getQueryRuntimes(performanceData, kb, engine);
    const gridDiv = document.querySelector("#details-grid");

    const rowCount = tableData.query.length;
    const rowData = getGridRowData(rowCount, tableData);
    gridDiv.innerHTML = "";
    let domLayout = "normal";
    if (rowCount < 25) domLayout = "autoHeight";

    if (domLayout === "normal") {
        gridDiv.style.height = `${document.documentElement.clientHeight - 200}px`;
    }
    let selectedRow = null;
    const detailsGridOptions = {
        columnDefs: getQueryRuntimesColumnDefs(),
        rowData: rowData,
        defaultColDef: {
            sortable: true,
            filter: true,
            resizable: true,
        },
        domLayout: domLayout,
        onGridReady: (params) => {
            detailsGridApi = params.api;
        },
        getRowStyle: (params) => {
            let rowStyle = { fontSize: "14px", cursor: "pointer" };
            if (params.data.failed === true) {
                rowStyle.backgroundColor = "#f6ccd0";
            }
            return rowStyle;
        },
        rowSelection: { mode: "singleRow", headerCheckbox: false, enableClickSelection: true },
        onRowSelected: (event) => {
            const query = Array.isArray(selectedRow) ? selectedRow[0].query : null;
            if (event.api.getSelectedRows()[0].query === query) return;
            selectedRow = event.api.getSelectedRows();
            onRuntimeRowSelected(event, performanceData, kb, engine);
        },
        tooltipShowDelay: 500,
    };
    // Initialize ag-Grid instance
    agGrid.createGrid(gridDiv, detailsGridOptions);
}
