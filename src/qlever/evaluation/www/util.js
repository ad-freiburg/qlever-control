var performanceData;
var router;
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

function showPage(pageId, siteErrorMsg = null) {
    // Hide all pages
    document.querySelectorAll(".page").forEach((p) => {
        p.classList.remove("visible");
        p.classList.add("hidden");
    });

    // Show requested page with animation
    const page = document.getElementById(`page-${pageId}`);
    if (page) {
        page.classList.remove("hidden");
        // Force reflow for transition to trigger
        void page.offsetWidth;
        page.classList.add("visible");
        if (pageId === "error" && siteErrorMsg !== null) {
            document.querySelector("#siteErrorMsg").innerText = siteErrorMsg;
        }
    }
}

function getGridRowData(rowCount, tableData) {
    return Array.from({ length: rowCount }, (_, i) => {
        const row = {};
        for (const col of Object.keys(tableData)) {
            row[col] = tableData[col][i];
        }
        return row;
    });
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

function addTextElementsToExecTreeForTreant(tree_node, is_ancestor_cached = false) {
    if (tree_node["text"] == undefined) {
        var text = {};
        if (tree_node["column_names"] == undefined) {
            tree_node["column_names"] = ["not yet available"];
        }
        // Rewrite runtime info from QLever as follows:
        //
        // 1. Abbreviate IRIs (only keep part after last / or # or dot)
        // 2. Remove qlc_ and _qlever_internal_... prefixes from variable names
        // 3. Lowercase fully capitalized words (with _)
        // 4. Separate CamelCase word parts by hyphen (Camel-Case)
        // 5. First word in ALL CAPS (like JOIN or INDEX-SCAN)
        // 6. Replace hyphen in all caps by space (INDEX SCAN)
        // 7. Abbreviate long QLever-internal variable names
        //
        text["name"] = tree_node["description"]
            .replace(/<[^>]*[#\/\.]([^>]*)>/g, "<$1>")
            .replace(/qlc_/g, "")
            .replace(/_qlever_internal_variable_query_planner/g, "")
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

        text["cols"] = tree_node["column_names"]
            .join(", ")
            .replace(/qlc_/g, "")
            .replace(/_qlever_internal_variable_query_planner/g, "")
            .replace(/\?[A-Z_]*/g, function (match) {
                return match.toLowerCase();
            });
        text["size"] = formatInteger(tree_node["result_rows"]) + " x " + formatInteger(tree_node["result_cols"]);
        text["size-estimate"] = "[~ " + formatInteger(tree_node["estimated_size"]) + "]";
        text["cache-status"] = is_ancestor_cached
            ? "ancestor_cached"
            : tree_node["cache_status"]
            ? tree_node["cache_status"]
            : tree_node["was_cached"]
            ? "cached_not_pinned"
            : "computed";
        text["time"] =
            tree_node["cache_status"] == "computed" || tree_node["was_cached"] == false
                ? formatInteger(tree_node["operation_time"])
                : formatInteger(tree_node["original_operation_time"]);
        text["cost-estimate"] = "[~ " + formatInteger(tree_node["estimated_operation_cost"]) + "]";
        text["status"] = tree_node["status"];
        if (text["status"] == "not started") {
            text["status"] = "not yet started";
        }
        text["total"] = text["time"];
        if (tree_node["details"]) {
            text["details"] = JSON.stringify(tree_node["details"]);
        }

        // Delete all other keys except "children" (we only needed them here to
        // create a proper "text" element) and the "text" element.
        for (var key in tree_node) {
            if (key != "children") {
                delete tree_node[key];
            }
        }
        tree_node["text"] = text;

        // Check out https://fperucic.github.io/treant-js
        // TODO: Do we still need / want this?
        tree_node["stackChildren"] = true;

        // Recurse over all children. Propagate "cached" status.
        tree_node["children"].map((child) =>
            addTextElementsToExecTreeForTreant(child, is_ancestor_cached || text["cache-status"] != "computed")
        );
    }
}

function formatInteger(number) {
    return number.toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1,");
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
