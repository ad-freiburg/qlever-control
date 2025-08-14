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
 * Returns ag-Grid gridOptions for comparing SPARQL engines for a given knowledge base.
 *
 * This grid displays various metrics like average time, failure rate, etc.
 * It applies proper formatting and filters based on the type of each metric.
 * @returns {Array<Object>} ag-Grid gridOptions object
 */
function mainTableColumnDefs(penaltyFactor) {
    // Define custom formatting and filters based on column keys
    return [
        {
            headerName: "SPARQL Engine",
            field: "engine_name",
            filter: "agTextColumnFilter",
            headerTooltip: "Name of the SPARQL engine being benchmarked.",
            tooltipComponent: CustomDetailsTooltip,
        },
        {
            headerName: "Failed",
            field: "failed",
            filter: "agNumberColumnFilter",
            type: "numericColumn",
            valueFormatter: ({ value }) => (value != null ? `${value.toFixed(2)}%` : "N/A"),
            headerTooltip: "Percentage of queries that failed to return results.",
            tooltipComponent: CustomDetailsTooltip,
        },
        {
            headerName: "Arithmetic Mean",
            field: "ameanTime",
            filter: "agNumberColumnFilter",
            type: "numericColumn",
            valueFormatter: ({ value }) => (value != null ? `${value.toFixed(2)}s` : "N/A"),
            headerTooltip: `Arithmetic mean of all query runtimes, including penalties for failed queries. (Runtime for failed queries = timeout * ${penaltyFactor})`,
            tooltipComponent: CustomDetailsTooltip,
        },
        {
            headerName: "Geometric Mean",
            field: "gmeanTime",
            filter: "agNumberColumnFilter",
            type: "numericColumn",
            valueFormatter: ({ value }) => (value != null ? `${value.toFixed(2)}s` : "N/A"),
            headerTooltip: `Geometric mean of all query runtimes, using log scale, includes failed query penalties. (Runtime for failed queries = timeout * ${penaltyFactor})`,
            tooltipComponent: CustomDetailsTooltip,
        },
        {
            headerName: "Median",
            field: "medianTime",
            filter: "agNumberColumnFilter",
            type: "numericColumn",
            valueFormatter: ({ value }) => (value != null ? `${value.toFixed(2)}s` : "N/A"),
            headerTooltip: `Median runtime of all queries, including penalties for failed ones. (Runtime for failed queries = timeout * ${penaltyFactor})`,
            tooltipComponent: CustomDetailsTooltip,
        },
        {
            headerName: "<= 1s",
            field: "under1s",
            filter: "agNumberColumnFilter",
            type: "numericColumn",
            valueFormatter: ({ value }) => (value != null ? `${value.toFixed(2)}%` : "N/A"),
            headerTooltip: "Percentage of successful queries that completed in 1 second or less.",
            tooltipComponent: CustomDetailsTooltip,
        },
        {
            headerName: "(1s, 5s]",
            field: "between1to5s",
            filter: "agNumberColumnFilter",
            type: "numericColumn",
            valueFormatter: ({ value }) => (value != null ? `${value.toFixed(2)}%` : "N/A"),
            headerTooltip: "Percentage of successful queries completed in more than 1 second and up to 5 seconds.",
            tooltipComponent: CustomDetailsTooltip,
        },
        {
            headerName: "> 5s",
            field: "over5s",
            filter: "agNumberColumnFilter",
            type: "numericColumn",
            valueFormatter: ({ value }) => (value != null ? `${value.toFixed(2)}%` : "N/A"),
            headerTooltip: "Percentage of successful queries that took more than 5 seconds to complete.",
            tooltipComponent: CustomDetailsTooltip,
        },
    ];
}

function updateMainPage(performanceData, additionalData) {
    document.querySelector("#main-page-header").innerHTML = "SPARQL Engine Comparison";
    const container = document.getElementById("main-table-container");

    // Clear container if any existing content
    container.innerHTML = "";

    // For each knowledge base (kb) key in performanceData
    for (const kb of Object.keys(performanceData)) {
        // Create section wrapper
        const section = document.createElement("div");
        section.className = "kg-section";

        // Header with KB name and a compare button
        const header = document.createElement("div");
        header.className = "kg-header";

        const titleWrapper = document.createElement("div");
        titleWrapper.className = "d-inline-flex align-items-center";

        const title = document.createElement("h5");
        title.textContent = capitalize(kb);
        title.style.fontWeight = "bold";
        title.classList.add("mb-1");

        const indexDescription = additionalData.kbs[kb].index_description;

        let infoPill = null;
        if (indexDescription) {
            infoPill = document.createElement("a");
            infoPill.setAttribute("tabindex", 0);
            infoPill.className = "badge bg-light text-dark border border-dark rounded-pill ms-2";
            infoPill.style.cursor = "pointer";
            infoPill.style.padding = "0.25em 0.45em";
            infoPill.style.fontSize = "0.65rem"; // smaller
            infoPill.style.lineHeight = "1";
            infoPill.style.textDecoration = "none";
            infoPill.textContent = "ℹ"; 
            infoPill.setAttribute("data-bs-toggle", "popover");
            infoPill.setAttribute("data-bs-trigger", "focus");
            infoPill.setAttribute("data-bs-placement", "right");
            infoPill.setAttribute("data-bs-html", "true");
            infoPill.setAttribute("data-bs-custom-class", "bg-dark");
            infoPill.setAttribute(
                "data-bs-content",
                anchorme({
                    input: indexDescription,
                    options: { attributes: { target: "_blank", class: "text-info" } },
                })
            );
        }

        const compareBtn = document.createElement("button");
        compareBtn.className = "btn btn-outline-dark btn-sm";
        compareBtn.textContent = "Compare Results";
        compareBtn.onclick = () => {
            router.navigate(`/comparison?kb=${encodeURIComponent(kb)}`);
        };

        titleWrapper.appendChild(title);
        if (infoPill) {
            titleWrapper.appendChild(infoPill);
            new bootstrap.Popover(infoPill);
        }
        header.appendChild(titleWrapper);
        header.appendChild(compareBtn);

        // Grid div with ag-theme-balham styling
        const gridDiv = document.createElement("div");
        gridDiv.className = "ag-theme-balham";
        gridDiv.style.width = "100%";

        // Append header and grid div to section
        section.appendChild(header);
        section.appendChild(gridDiv);
        container.appendChild(section);

        // Get table data from function you provided
        const tableData = getAllQueryStatsByKb(performanceData, kb);

        // Prepare row data as array of objects for ag-grid
        // tableData is {colName: [val, val, ...], ...}
        // We convert to [{engine_name: ..., ameanTime: ..., ...}, ...]
        const rowCount = tableData.engine_name.length;
        const rowData = getGridRowData(rowCount, tableData);

        const onRowClicked = (event) => {
            const engine = event.data.engine_name.toLowerCase();
            router.navigate(`/details?kb=${encodeURIComponent(kb)}&engine=${encodeURIComponent(engine)}`);
        };

        const penaltyFactor = additionalData.penalty?.toString() ?? "Penalty Factor";

        // Initialize ag-Grid instance
        agGrid.createGrid(gridDiv, {
            columnDefs: mainTableColumnDefs(penaltyFactor),
            rowData: rowData,
            defaultColDef: {
                sortable: true,
                filter: true,
                resizable: true,
                flex: 1,
                minWidth: 100,
            },
            domLayout: "autoHeight",
            rowStyle: { fontSize: "14px", cursor: "pointer" },
            tooltipShowDelay: 500,
            onRowClicked: onRowClicked,
            suppressDragLeaveHidesColumns: true,
        });
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    router = new Navigo("/", { hash: true });

    try {
        const yaml_path = window.location.origin + window.location.pathname.replace(/\/$/, "").replace(/\/[^/]*$/, "/");
        const response = await fetch(`${yaml_path}yaml_data`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        performanceData = data.performance_data;
        const additionalData = data.additional_data;

        for (const kb in performanceData) {
            for (const engine in performanceData[kb]) {
                const queries = performanceData[kb][engine].queries;
                if (Array.isArray(queries)) {
                    queries.forEach((query) => {
                        try {
                            query.sparql = spfmt.format(query.sparql);
                        }
                        catch (err) {
                            console.log(err);
                        }
                    });
                }
            }
        }

        // Routes
        router
            .on({
                "/": () => {
                    showPage("main");
                    updateMainPage(performanceData, additionalData);
                },
                "/details": (params) => {
                    const kb = params.params.kb;
                    const engine = params.params.engine;
                    if (
                        !Object.keys(performanceData).includes(kb) ||
                        !Object.keys(performanceData[kb]).includes(engine)
                    ) {
                        showPage(
                            "error",
                            `Query Details Page not found for ${engine} (${kb}) -> Make sure the url is correct!`
                        );
                        return;
                    }
                    updateDetailsPage(performanceData, kb, engine);
                    showPage("details");
                },
                "/comparison": (params) => {
                    const kb = params.params.kb;
                    if (!Object.keys(performanceData).includes(kb)) {
                        showPage(
                            "error",
                            `Performance Comparison Page not found for ${capitalize(
                                kb
                            )} -> Make sure the url is correct!`
                        );
                        return;
                    }
                    updateComparisonPage(performanceData, kb);
                    showPage("comparison");
                },
                "/compareExecTrees": (params) => {
                    const kb = params.params.kb;
                    const queryIdx = params.params.q;
                    if (!Object.keys(performanceData).includes(kb)) {
                        showPage(
                            "error",
                            `Query Execution Tree Page not found for ${capitalize(kb)} -> Make sure the url is correct!`
                        );
                        return;
                    }
                    const queryToEngineStats = getQueryToEngineStatsDict(performanceData[kb]);
                    if (
                        isNaN(parseInt(queryIdx)) ||
                        parseInt(queryIdx) < 0 ||
                        parseInt(queryIdx) >= Object.keys(queryToEngineStats).length
                    ) {
                        showPage(
                            "error",
                            `Query Execution Tree Page not found as the requested query is not available for ${capitalize(
                                kb
                            )} -> Make sure the parameter q in the url is correct!`
                        );
                        return;
                    }
                    const execTreeEngines = getEnginesWithExecTrees(performanceData[kb]);
                    const query = Object.keys(queryToEngineStats)[queryIdx];

                    const engineStatForQuery = Object.fromEntries(
                        Object.entries(queryToEngineStats[query]).filter(([engine]) => execTreeEngines.includes(engine))
                    );
                    updateCompareExecTreesPage(kb, query, engineStatForQuery);
                    showPage("compareExecTrees");
                },
            })
            .notFound(() => {
                showPage("main");
                updateMainPage(performanceData, additionalData);
            });

        router.resolve();

        setDetailsPageEvents();
        setComparisonPageEvents();
        setCompareExecTreesEvents();
    } catch (err) {
        console.error("Error loading /yaml_data:", err);
        showPage("error");
    }
});
