let gridApi;
/**
 * Populate the checkbox container inside the accordion with column names.
 * @param {string[]} columnNames - List of Ag Grid column field names
 */
function populateColumnCheckboxes(columnNames) {
    const container = document.querySelector("#columnCheckboxContainer");
    container.innerHTML = "";

    columnNames.forEach((col) => {
        const div = document.createElement("div");
        div.classList.add("form-check");

        const checkbox = document.createElement("input");
        checkbox.className = "form-check-input";
        checkbox.style.cursor = "pointer";
        checkbox.type = "checkbox";
        checkbox.id = `col-${col}`;
        checkbox.value = col;
        checkbox.checked = true;

        const label = document.createElement("label");
        label.className = "form-check-label";
        label.style.cursor = "pointer";
        label.setAttribute("for", `col-${col}`);
        label.textContent = capitalize(col);

        div.appendChild(checkbox);
        div.appendChild(label);
        container.appendChild(div);
    });
}

function setComparisonPageEvents() {
    document.querySelector("#columnCheckboxContainer").addEventListener("change", (event) => {
        if (event.target && event.target.matches('input[type="checkbox"]')) {
            const enginesToDisplay = Array.from(
                document.querySelectorAll('#columnCheckboxContainer input[type="checkbox"]:checked')
            ).map((cb) => cb.value);
            // console.log("Currently checked:", selectedValues);
            updateHiddenColumns(enginesToDisplay);
            // You can now use selectedValues to hide/show columns, etc.
        }
    });

    document.querySelector("#orderColumnsDropdown").addEventListener("change", (event) => {
        const selectedValue = event.target.value;
        const [metric, order] = selectedValue.split("-");
        const kb = document.querySelector("#page-comparison").dataset.kb;
        const enginesToDisplay = Array.from(
            document.querySelectorAll('#columnCheckboxContainer input[type="checkbox"]:checked')
        ).map((cb) => cb.value);
        const sortedEngines = sortEngines(enginesToDisplay, kb, metric, order);
        const showResultSize = document.querySelector("#showResultSize").checked;
        const sortedColumnDefs = getComparisonColumnDefs(sortedEngines, showResultSize);
        const showMetrics = document.querySelector("#showMetrics").checked;
        sortedColumnDefs[0].headerName = showMetrics ? "Metric/Query" : "Query";
        const colState = gridApi.getColumnState();
        gridApi.updateGridOptions({
            columnDefs: sortedColumnDefs,
            maintainColumnOrder: false,
        });
        gridApi.applyColumnState({
            state: colState,
        });
    });

    document.querySelector("#showMetrics").addEventListener("change", (event) => {
        if (!gridApi) return;
        const showMetrics = event.target.checked;
        const enginesToDisplay = gridApi
            .getColumns()
            .filter((col) => {
                return col.colId !== "query";
            })
            .map((col) => {
                return col.colId;
            });
        const columnDefs = gridApi.getColumnDefs();
        let pinnedMetricData = [];
        let queryHeader = "Query";
        if (showMetrics) {
            const kb = document.querySelector("#page-comparison").dataset.kb;
            pinnedMetricData = getPinnedMetricData(enginesToDisplay, kb);
            queryHeader = "Metric/Query";
        }
        columnDefs[0].headerName = queryHeader;
        const colState = gridApi.getColumnState();
        gridApi.updateGridOptions({
            pinnedTopRowData: pinnedMetricData,
            columnDefs: columnDefs,
        });
        gridApi.applyColumnState({
            state: colState,
        });
    });

    document.querySelector("#showResultSize").addEventListener("change", (event) => {
        if (!gridApi) return;
        const showResultSize = event.target.checked;
        const enginesToDisplay = gridApi
            .getColumns()
            .filter((col) => {
                return col.colId !== "query";
            })
            .map((col) => {
                return col.colId;
            });
        const visibleColumnDefs = getComparisonColumnDefs(enginesToDisplay, showResultSize);
        const showMetrics = document.querySelector("#showMetrics").checked;
        visibleColumnDefs[0].headerName = showMetrics ? "Metric/Query" : "Query";
        const colState = gridApi.getColumnState();
        gridApi.updateGridOptions({
            columnDefs: visibleColumnDefs,
            maintainColumnOrder: true,
        });
        gridApi.applyColumnState({
            state: colState,
        });
    });

    document.querySelector("#goToCompareExecTreesBtn").addEventListener("click", () => {
        goToCompareExecTreesPage(gridApi, "Performance Comparison");
    });

    document.querySelector("#comparisonDownloadTsv").addEventListener("click", () => {
        const kb = document.querySelector("#page-comparison").dataset.kb;
        if (!gridApi) {
            alert(`The evaluation results table for ${kb} could not be downloaded!`);
            return;
        }
        gridApi.exportDataAsCsv({
            fileName: `${kb}_evaluation_results.tsv`,
            columnSeparator: "\t",
        });
    });
}

/**
 * Constructs a mapping from query string to engine-specific stats.
 * @param {Object} performanceData - The top-level engine performance data.
 * @returns {Object} queryToEngineStatsDict - Mapping: query => { engine => stats }
 */
function getQueryToEngineStatsDict(performanceData) {
    const queryToEngineStatsDict = {};

    for (const [engine, data] of Object.entries(performanceData)) {
        const queriesData = data.queries;

        for (const queryData of queriesData) {
            const { query, ...restOfStats } = queryData;

            if (!queryToEngineStatsDict[query]) {
                queryToEngineStatsDict[query] = {};
            }

            queryToEngineStatsDict[query][engine] = restOfStats;
        }
    }

    return queryToEngineStatsDict;
}

/**
 * Finds the best (lowest) runtime among all engines for a single query.
 * @param {Object} engineStats - Stats per engine for a query.
 * @returns {number|null} - Minimum runtime or null if no valid runtimes.
 */
function getBestRuntimeForQuery(engineStats) {
    const runtimes = Object.values(engineStats)
        .filter((stat) => typeof stat.results !== "string")
        .map((stat) => Number(stat.runtime_info.client_time.toFixed(2)));

    return runtimes.length > 0 ? Math.min(...runtimes) : null;
}

/**
 * Determines the majority result size or single result value for a query across engines.
 * @param {Object} engineStats - Stats per engine.
 * @returns {string|null} - The majority size string, or "no_consensus", or null.
 */
function getMajorityResultSizeForQuery(engineStats) {
    const sizeCounts = {};

    for (const stat of Object.values(engineStats)) {
        if (typeof stat.results === "string") continue;

        const singleResult = getSingleResult(stat);
        const resultSize = stat.result_size ?? 0;
        const key = singleResult === null ? resultSize.toLocaleString() : singleResult;

        sizeCounts[key] = (sizeCounts[key] || 0) + 1;
    }

    const entries = Object.entries(sizeCounts);
    if (entries.length === 0) return null;

    let [majorityResultSize, maxCount, tie] = [null, 0, false];

    for (const [size, count] of entries) {
        if (count > maxCount) {
            majorityResultSize = size;
            maxCount = count;
            tie = false;
        } else if (count === maxCount) {
            tie = true;
        }
    }

    return tie ? "no_consensus" : majorityResultSize;
}

/**
 * Creates a summary of performance per query per engine for display.
 * @param {Object} performanceData - Raw engine performance data.
 * @returns {Object} A structured object ready for use with AG Grid or tables.
 */
function getPerformanceComparisonPerKbDict(allEngineStats, enginesToDisplay = null) {
    enginesToDisplay = enginesToDisplay === null ? Object.keys(allEngineStats) : enginesToDisplay;
    const performanceData = Object.fromEntries(
        Object.entries(allEngineStats).filter(([key]) => enginesToDisplay.includes(key))
    );
    const engineNames = Object.keys(performanceData);
    const columns = ["query", "row_warning", ...engineNames.flatMap((e) => [e, `${e}_stats`])];

    const result = {};
    for (const col of columns) result[col] = [];

    const queryToEngineStats = getQueryToEngineStatsDict(performanceData);

    for (const [query, engineStats] of Object.entries(queryToEngineStats)) {
        result["query"].push(query);

        const bestRuntime = getBestRuntimeForQuery(engineStats);
        const majoritySize = getMajorityResultSizeForQuery(engineStats);
        result["row_warning"].push(majoritySize === "no_consensus");

        for (const engine of engineNames) {
            const stat = engineStats[engine];
            if (!stat) {
                result[engine].push(null);
                result[`${engine}_stats`].push(null);
                continue;
            }

            const runtime = Number(stat.runtime_info.client_time.toFixed(2));
            const singleResult = getSingleResult(stat);
            const resultSize = stat.result_size ?? 0;
            const resultSizeFinal = singleResult === null ? resultSize.toLocaleString() : singleResult;

            const sizeWarning =
                majoritySize !== "no_consensus" &&
                majoritySize !== null &&
                typeof stat.results !== "string" &&
                resultSizeFinal !== majoritySize;

            Object.assign(stat, {
                has_best_runtime: runtime === bestRuntime,
                majority_result_size: majoritySize,
                size_warning: sizeWarning,
                result_size_to_display: singleResult === null ? resultSize.toLocaleString() : `1 [${singleResult}]`,
            });

            result[engine].push(runtime);
            result[`${engine}_stats`].push(stat);
        }
    }

    return result; // or convert to tabular UI (e.g., AG Grid rows)
}

// Function to update column visibility
function updateHiddenColumns(enginesToDisplay) {
    if (!gridApi) return;

    const kb = document.querySelector("#page-comparison").dataset.kb;
    const visibleTableData = getPerformanceComparisonPerKbDict(performanceData[kb], enginesToDisplay);
    const visibleRowData = getGridRowData(visibleTableData.query.length, visibleTableData);
    // gridApi.setGridOption("rowData", visibleRowData);
    const showResultSize = document.querySelector("#showResultSize").checked;
    const [metric, order] = document.querySelector("#orderColumnsDropdown").value.split("-");
    const sortedEngines = sortEngines(enginesToDisplay, kb, metric, order);
    const visibleColumnDefs = getComparisonColumnDefs(sortedEngines, showResultSize);
    const showMetrics = document.querySelector("#showMetrics").checked;
    visibleColumnDefs[0].headerName = showMetrics ? "Metric/Query" : "Query";
    const colState = gridApi.getColumnState();
    gridApi.updateGridOptions({
        columnDefs: visibleColumnDefs,
        rowData: visibleRowData,
        maintainColumnOrder: false,
    });
    gridApi.applyColumnState({
        state: colState,
    });
}

class WarningCellRenderer {
    init(params) {
        if (params.pinned) console.log(params);
        const value = params.value;
        const container = document.createElement("div");
        container.style.whiteSpace = "normal";

        const warning = document.createElement("span");
        warning.textContent = "⚠️";
        warning.style.marginRight = "4px";

        if (params.node.rowPinned) {
            container.classList.add("fw-bold");
            if (typeof value === "string") {
                container.appendChild(document.createTextNode(`${value}`));
            } else {
                const unit = params.data.query === "Failed Queries" ? "%" : "s";
                container.appendChild(document.createTextNode(`${value.toFixed(2)} ${unit}`));
            }
        } else if (params.column.getColId() === "query") {
            container.appendChild(document.createTextNode(`${value}  `));
            if (params.data.row_warning) {
                warning.title = "The result sizes for the engines do not match!";
                container.appendChild(warning);
            }
        } else {
            const engineStatsColumn = params.column.getColId() + "_stats";
            const engineStats = params.data[engineStatsColumn];
            if (engineStats && typeof engineStats === "object" && engineStats.size_warning) {
                warning.title = `Result size ${engineStats.result_size_to_display} doesn't match the majority ${engineStats.majority_result_size}!`;
                container.appendChild(warning);
            }
            container.appendChild(document.createTextNode(`${value} s`));
            if (params.showResultSize) {
                //container.appendChild(document.createElement("br"));
                const resultSizeLine = document.createElement("div");
                resultSizeLine.textContent = engineStats?.result_size_to_display;
                resultSizeLine.style.color = "#888";
                resultSizeLine.style.fontSize = "90%";
                resultSizeLine.style.marginTop = "-8px";
                // container.appendChild(document.createTextNode(engineStats.result_size_to_display));
                container.appendChild(resultSizeLine);
            }
        }
        this.eGui = container;
    }

    getGui() {
        return this.eGui;
    }
}

function comparisonGridCellStyle(params) {
    const engineStatsColumn = params.column.getColId() + "_stats";
    const engineStats = params.data[engineStatsColumn];

    if (engineStats && typeof engineStats === "object") {
        if (typeof engineStats.results === "string") {
            return { backgroundColor: "#f6ccd0" };
        } else if (engineStats.has_best_runtime) {
            return { backgroundColor: "#c5e1d4" };
        }
    }
    return {};
}

function getTooltipValue(params) {
    if (params.column.getColId() === "query") {
        for (const key in params.data) {
            const value = params.data[key];
            if (value && typeof value === "object" && typeof value.sparql === "string") {
                return { title: value.description || "", sparql: value.sparql || "" };
            }
        }
        return null;
    }
    const engineStatsColumn = params.column.getColId() + "_stats";
    const engineStats = params.data[engineStatsColumn];

    if (engineStats && typeof engineStats === "object") {
        if (typeof engineStats.results === "string") {
            return engineStats.results;
        } else {
            return `Result size: ${engineStats.result_size_to_display}`;
        }
    }
    return null;
}

class CustomTooltip {
    init(params) {
        const container = createTooltipContainer(params);

        if (window.isSecureContext) {
            // Copy button
            const copyButton = document.createElement("button");
            copyButton.innerHTML = "📄";
            copyButton.className = "copy-btn";
            copyButton.title = "Copy";
    
            copyButton.onclick = () => {
                navigator.clipboard
                    .writeText(tooltipText)
                    .then(() => {
                        copyButton.innerHTML = "✅";
                        setTimeout(() => (copyButton.innerHTML = "📋"), 1000);
                    })
                    .catch((err) => {
                        console.error("Failed to copy full SPARQL query:", err);
                        copyButton.innerHTML = "❌";
                        setTimeout(() => (copyButton.innerHTML = "📋"), 1000);
                    });
            };
    
            container.appendChild(copyButton);
        }

        this.eGui = container;
    }

    getGui() {
        return this.eGui;
    }
}

function getPinnedMetricData(engines, kb) {
    let pinnedMetricData = [];
    const metricKeyNameObj = {
        gmeanTime: "Geometric Mean",
        failed: "Failed Queries",
        medianTime: "Median",
        ameanTime: "Arithmetic Mean",
    };
    for (const [metric, metricName] of Object.entries(metricKeyNameObj)) {
        let metricData = { query: metricName };
        for (const engine of engines) {
            metricData[engine] = performanceData[kb][engine][metric];
        }
        pinnedMetricData.push(metricData);
    }
    return pinnedMetricData;
}

/**
 * Returns column definitions for ag-Grid to display engine comparison results.
 *
 * @returns {Array<Object>} columnDefs for ag-Grid
 */
function getComparisonColumnDefs(engines, showResultSize) {
    columnDefs = [
        {
            headerName: "Query",
            field: "query",
            filter: "agTextColumnFilter",
            flex: 4,
            cellRenderer: WarningCellRenderer,
            autoHeight: showResultSize,
            tooltipValueGetter: getTooltipValue,
            tooltipComponent: CustomTooltip,
        },
    ];
    for (const engine of engines) {
        columnDefs.push({
            field: engine,
            type: "numericColumn",
            filter: "agNumberColumnFilter",
            flex: 1,
            cellRenderer: WarningCellRenderer,
            cellRendererParams: { showResultSize: showResultSize },
            cellStyle: comparisonGridCellStyle,
            autoHeight: true,
            tooltipValueGetter: getTooltipValue,
            tooltipComponent: CustomTooltip,
        });
    }
    return columnDefs;
}

function updateComparisonPage(performanceData, kb, kbAdditionalData) {
    const pageNode = document.querySelector("#page-comparison");
    const lastKb = pageNode.dataset.kb;
    removeTitleInfoPill();
    const titleNode = document.querySelector("#main-page-header");
    let title = `Performance comparison for ${capitalize(kb)}`;
    if (kbAdditionalData.title) title = kbAdditionalData.title;
    let infoPill = null;
    if (kbAdditionalData.description) {
        infoPill = createBenchmarkDescriptionInfoPill(kbAdditionalData.description, false, "bottom");
    }
    if (infoPill) {
        document.querySelector("#mainTitleWrapper").appendChild(infoPill);
        new bootstrap.Popover(infoPill);
    }
    titleNode.innerHTML = title;
    if (lastKb === kb) return;
    pageNode.dataset.kb = kb;
    document.querySelector("#orderColumnsDropdown").selectedIndex = 0;

    populateColumnCheckboxes(Object.keys(performanceData[kb]));
    document.querySelector("#showResultSize").checked = false;
    document.querySelector("#showMetrics").checked = false;
    let rowSelection = undefined;
    const execTreeEngines = getEnginesWithExecTrees(performanceData[kb]);
    if (execTreeEngines.length < 2) {
        document.querySelector("#goToCompareExecTreesBtn").classList.add("d-none");
    } else {
        document.querySelector("#goToCompareExecTreesBtn").classList.remove("d-none");
        rowSelection = { mode: "singleRow", headerCheckbox: false };
    }

    const tableData = getPerformanceComparisonPerKbDict(performanceData[kb]);
    const gridDiv = document.querySelector("#comparison-grid");

    const rowCount = tableData.query.length;
    const rowData = getGridRowData(rowCount, tableData);
    gridDiv.innerHTML = "";
    let domLayout = "normal";
    if (rowCount < 25) domLayout = "autoHeight";

    if (domLayout === "normal") {
        gridDiv.style.height = `${document.documentElement.clientHeight - 235}px`;
    }
    // Default column ordering = first option of orderColumnsDropdown
    const sortedEngines = sortEngines(Object.keys(performanceData[kb]), kb, "gmeanTime", "asc");
    const comparisonGridOptions = {
        columnDefs: getComparisonColumnDefs(sortedEngines),
        rowData: rowData,
        defaultColDef: {
            sortable: true,
            filter: true,
            resizable: true,
            flex: 1,
            minWidth: 100,
        },
        domLayout: domLayout,
        rowStyle: { fontSize: "14px", cursor: "pointer" },
        onGridReady: (params) => {
            gridApi = params.api;
        },
        tooltipShowDelay: 0,
        tooltipTrigger: "focus",
        tooltipInteraction: true,
        rowSelection: rowSelection,
        suppressDragLeaveHidesColumns: true,
    };
    // Initialize ag-Grid instance
    agGrid.createGrid(gridDiv, comparisonGridOptions);
}
