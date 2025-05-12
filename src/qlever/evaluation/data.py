from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import yaml
from st_aggrid import GridOptionsBuilder, JsCode

METRIC_KEYS = [
    "failed",
    "gmeanTime",
    "ameanTime",
    "medianTime",
    "under1s",
    "between1to5s",
    "over5s",
]


def get_query_stats(queries: list[dict]) -> dict[str, float | None]:
    query_data = {
        "ameanTime": None,
        "gmeanTime": None,
        "medianTime": None,
        "under1s": 0.0,
        "between1to5s": 0.0,
        "over5s": 0.0,
        "failed": 0.0,
    }
    failed = under_1 = bw_1_to_5 = over_5 = 0
    total_time = total_log_time = 0.0
    runtimes = []
    for query in queries:
        if len(query["headers"]) == 0 and isinstance(query["results"], str):
            failed += 1
        else:
            runtime = float(query["runtime_info"]["client_time"])
            total_time += runtime
            total_log_time += max(math.log(runtime), 0.001)
            runtimes.append(runtime)
            if runtime <= 1:
                under_1 += 1
            elif runtime > 5:
                over_5 += 1
            else:
                bw_1_to_5 += 1
    total_successful = len(runtimes)
    if total_successful == 0:
        query_data["failed"] = 100.0
    else:
        query_data["ameanTime"] = total_time / total_successful
        query_data["gmeanTime"] = math.exp(total_log_time / total_successful)
        query_data["medianTime"] = sorted(runtimes)[total_successful // 2]
        query_data["under1s"] = (under_1 / total_successful) * 100
        query_data["between1to5s"] = (bw_1_to_5 / total_successful) * 100
        query_data["over5s"] = (over_5 / total_successful) * 100
        query_data["failed"] = (failed / len(queries)) * 100
    return query_data


def create_performance_data(yaml_dir: Path) -> dict | None:
    performance_data = {}
    if not yaml_dir.is_dir():
        return None
    for yaml_file in yaml_dir.glob("*.results.yaml"):
        file_name_split = yaml_file.stem.split(".")
        if len(file_name_split) != 3:
            continue
        dataset, engine, _ = file_name_split
        if performance_data.get(dataset) is None:
            performance_data[dataset] = {}
        if performance_data[dataset].get(engine) is None:
            performance_data[dataset][engine] = {}
        with yaml_file.open("r", encoding="utf-8") as queries_file:
            queries_data = yaml.safe_load(queries_file)
            query_stats = get_query_stats(queries_data["queries"])
            performance_data[dataset][engine] = {**query_stats, **queries_data}
    return performance_data


results_dir = os.environ.get("QLEVER_YAML_RESULTS_DIR")
yaml_data = create_performance_data(Path(results_dir))


def remove_top_padding() -> None:
    # Custom CSS to remove top padding
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1rem;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )


def get_all_query_stats_by_kb(
    performance_data: dict[str, dict[str, float | list]], kb: str
) -> pd.DataFrame:
    engines_dict = performance_data[kb]
    engines_dict_for_df = {col: [] for col in ["engine_name"] + METRIC_KEYS}
    for engine, engine_stats in engines_dict.items():
        engines_dict_for_df["engine_name"].append(engine.capitalize())
        for metric_key in METRIC_KEYS:
            metric = engine_stats[metric_key]
            engines_dict_for_df[metric_key].append(metric)
    return pd.DataFrame.from_dict(engines_dict_for_df)


def extract_core_value(sparql_value: Any) -> str:
    if isinstance(sparql_value, list):
        if not sparql_value:
            return ""
        sparql_value = sparql_value[0]

    if not isinstance(sparql_value, str) or not sparql_value.strip():
        return ""

    # URI enclosed in angle brackets
    if sparql_value.startswith("<") and sparql_value.endswith(">"):
        return sparql_value[1:-1]

    # Literal string (e.g., "\"Some value\"")
    literal_match = re.match(r'^"((?:[^"\\]|\\.)*)"', sparql_value)
    if literal_match:
        raw = literal_match.group(1)
        return re.sub(r"\\(.)", r"\1", raw)

    # Fallback
    return sparql_value


def get_query_runtimes(
    performance_data: dict[str, dict[str, float | list]], kb: str, engine: str
) -> pd.DataFrame:
    all_queries_data = performance_data[kb][engine]["queries"]
    query_runtimes_for_df = {
        "query": [],
        "runtime": [],
        "failed": [],
        "result_size": [],
    }
    for query_data in all_queries_data:
        query_runtimes_for_df["query"].append(query_data["query"])
        runtime = round(query_data["runtime_info"]["client_time"], 2)
        query_runtimes_for_df["runtime"].append(runtime)
        failed = (
            isinstance(query_data["results"], str)
            or len(query_data["headers"]) == 0
        )
        query_runtimes_for_df["failed"].append(failed)
        result_size = query_data.get("result_size")
        result_size = 0 if result_size is None else result_size
        single_result = get_single_result(query_data)
        result_size_to_display = (
            f"{result_size:,}"
            if single_result is None
            else f"1 [{single_result}]"
        )
        query_runtimes_for_df["result_size"].append(result_size_to_display)
    return pd.DataFrame.from_dict(query_runtimes_for_df)


def get_single_result(query_data):
    result_size = query_data.get("result_size")
    result_size = 0 if result_size is None else result_size
    single_result = None
    if (
        result_size == 1
        and len(query_data["headers"]) == 1
        and len(query_data["results"]) == 1
    ):
        single_result = query_data["results"][0]
        single_result = extract_core_value(single_result)
        try:
            single_result = f"{int(single_result):,}"
        except ValueError:
            pass
    return single_result


def grid_options_for_runtimes_df() -> dict:
    gb = GridOptionsBuilder()
    # makes columns resizable, sortable and filterable by default
    gb.configure_default_column(
        resizable=True,
        sortable=True,
        editable=False,
    )

    gb.configure_column(
        field="query",
        header_name="Query",
        flex=4,
        filter="agTextColumnFilter",
    )
    gb.configure_column(
        field="runtime",
        header_name="Runtime (s)",
        type="numericColumn",
        flex=1,
        filter="agNumberColumnFilter",
    )
    gb.configure_column(
        field="result_size",
        header_name="Result size",
        type="numericColumn",
        flex=1.5,
        filter="agTextColumnFilter",
    )
    row_style_jscode = JsCode("""
        function(params) {
            if (params.data.failed === true) {
                return {'color': 'red'};
            }
            return {};
        }
    """)

    # gb.configure_auto_height()
    gb.configure_grid_options(getRowStyle=row_style_jscode)
    gb.configure_selection()
    return gb.build()


def get_query_results_df(
    headers: list[str], query_results: list[list[str]]
) -> pd.DataFrame:
    query_results_lists = [[] for _ in headers]
    for result in query_results:
        for i in range(len(headers)):
            query_results_lists[i].append(result[i])
    query_results_for_df = {
        header: query_results_lists[i] for i, header in enumerate(headers)
    }
    return pd.DataFrame.from_dict(query_results_for_df)


def grid_options_for_comparison_df(
    engines: list[str], engines_to_hide: list[str] | None = None
) -> dict:
    gb = GridOptionsBuilder()
    # makes columns resizable, sortable and filterable by default
    gb.configure_default_column(
        resizable=True,
        sortable=True,
        editable=False,
    )

    cell_renderer_js = JsCode("""
        class WarningCellRenderer {
            init(params) {
                const value = params.value;
                const container = document.createElement("span");

                const warning = document.createElement("span");
                warning.textContent = "⚠️";
                warning.style.color = "red";
                warning.style.marginRight = "4px";

                if (params.column.getColId() === "Query") {
                    container.appendChild(document.createTextNode(value));
                    if (params.data.row_warning) {
                        container.appendChild(warning);
                    }
                } else {
                    const engineStatsColumn = params.column.getColId() + "_stats";
                    const engineStats = params.data[engineStatsColumn];
                    if (engineStats && typeof engineStats === "object" && engineStats.size_warning) {
                        container.appendChild(warning);
                    }                
                    container.appendChild(document.createTextNode(`${value} s`));
                }
                this.eGui = container;
            }

            getGui() {
                return this.eGui;
            }
        }
    """)

    cell_style_jscode = JsCode("""
        function(params) {
            const engineStatsColumn = params.column.getColId() + "_stats";
            const engineStats = params.data[engineStatsColumn];

            if (engineStats && typeof engineStats === "object") {
                if (typeof engineStats.results === "string") {
                    return { color: 'red' };
                }
                else if (engineStats.has_best_runtime) {
                    return { color: 'green' };
                }
            }
            return {};
        }
    """)

    tooltip_js = JsCode("""
    function(params) {
            if (params.column.getColId() === "Query") {
                for (const key in params.data) {
                    const value = params.data[key];
                    if (value && typeof value === 'object' && typeof value.sparql === 'string') {
                        return value.sparql;
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
    """)

    sparql_tooltip_js = JsCode("""
        class CustomTooltip  {
            eGui;
            init(params) {
                const eGui = (this.eGui = document.createElement('div'));
                eGui.style.backgroundColor = '#363636';
                eGui.style.color = '#fff';
                eGui.style.whiteSpace = 'pre-wrap';
                eGui.style.fontFamily = 'sans-serif';
                eGui.style.fontSize = '12px';
                eGui.style.padding = '4px';

                let tooltipText;
                if (params.column.getColId() === "Query") {
                    tooltipText = params.data.row_warning 
                        ? "The result sizes for the engines do not match!<br><br>" 
                        : "";
                    tooltipText += params.value;
                } else {
                    const engineStatsColumn = params.column.getColId() + "_stats";
                    const engineStats = params.data[engineStatsColumn];
                    tooltipText = params.value;
                    if (engineStats && typeof engineStats === "object" && engineStats.size_warning) {
                        tooltipText += `<br>Result size ${engineStats.result_size_to_display} doesn't match the majority ${engineStats.majority_result_size}!`;
                    }  
                }
                eGui.innerHTML = `
                    <div>${tooltipText}</div>
                `;
            }

            getGui() {
                return this.eGui;
            }
        }
    """)

    gb.configure_column(
        field="Query",
        flex=4,
        cellRenderer=cell_renderer_js,
        tooltipValueGetter=tooltip_js,
        tooltipComponent=sparql_tooltip_js,
        filter="agTextColumnFilter",
    )
    for engine in engines:
        gb.configure_column(
            field=engine,
            type="numericColumn",
            flex=1,
            cellRenderer=cell_renderer_js,
            cellStyle=cell_style_jscode,
            tooltipValueGetter=tooltip_js,
            tooltipComponent=sparql_tooltip_js,
            filter="agNumberColumnFilter",
            hide=(engine in engines_to_hide),
        )

    gb.configure_grid_options(tooltipShowDelay=0, tooltipInteraction=True)
    return gb.build()


def get_query_to_engine_stats_dict(
    performance_data: dict[str, float | list],
) -> dict[str, dict[str, Any]]:
    query_to_engine_stats_dict = {}
    for engine in performance_data:
        queries_data = performance_data[engine]["queries"]
        for query_data in queries_data:
            query_str = query_data["query"]
            rest_of_the_dict = {
                k: v for k, v in query_data.items() if k != "query"
            }

            if query_str not in query_to_engine_stats_dict:
                query_to_engine_stats_dict[query_str] = {}
            query_to_engine_stats_dict[query_str][engine] = rest_of_the_dict
    return query_to_engine_stats_dict


def get_best_runtime_for_query(engine_stats: dict[str, Any]) -> float | None:
    runtimes = [
        round(engine_data["runtime_info"]["client_time"], 2)
        for engine_data in engine_stats.values()
        if not isinstance(engine_data["results"], str)
    ]
    return None if len(runtimes) == 0 else min(runtimes)


def get_majority_result_size_for_query(engine_stats: dict[str, Any]):
    size_counts = {}
    for engine_data in engine_stats.values():
        if isinstance(engine_data["results"], str):
            continue
        single_result = get_single_result(engine_data)
        result_size = engine_data.get("result_size") or 0
        key = f"{result_size:,}" if single_result is None else single_result
        size_counts[key] = size_counts.get(key, 0) + 1
    if not size_counts:
        return None

    majority_result_size = None
    max_count = 0
    tie = False
    for size, count in size_counts.items():
        if count > max_count:
            max_count = count
            majority_result_size = size
            tie = False
        elif count == max_count:
            tie = True
    return "no_consensus" if tie else majority_result_size


def get_performance_comparison_per_kb_df(
    performance_data: dict[str, float | list],
) -> pd.DataFrame:
    engine_columns = []
    for engine in performance_data:
        engine_columns.append(engine)
        engine_columns.append(f"{engine}_stats")
    performance_data_per_kb_for_df = {
        col: [] for col in ["Query", "row_warning"] + engine_columns
    }
    query_to_engine_stats_dict = get_query_to_engine_stats_dict(
        performance_data
    )
    for query_str, engine_stats in query_to_engine_stats_dict.items():
        performance_data_per_kb_for_df["Query"].append(query_str)
        best_runtime = get_best_runtime_for_query(engine_stats)
        majority_result_size = get_majority_result_size_for_query(engine_stats)
        performance_data_per_kb_for_df["row_warning"].append(
            True if majority_result_size == "no_consensus" else False
        )
        for engine, stat in engine_stats.items():
            runtime = round(stat["runtime_info"]["client_time"], 2)
            stat["has_best_runtime"] = (
                True if runtime == best_runtime else False
            )
            stat["majority_result_size"] = majority_result_size
            size_warning = False
            single_result = get_single_result(stat)
            result_size = stat.get("result_size") or 0
            if majority_result_size not in (
                "no_consensus",
                None,
            ) and not isinstance(stat["results"], str):
                result_size_final = (
                    f"{result_size:,}"
                    if single_result is None
                    else str(single_result)
                )
                if majority_result_size != result_size_final:
                    size_warning = True

            stat["size_warning"] = size_warning
            stat["result_size_to_display"] = (
                f"{result_size:,}"
                if single_result is None
                else f"1 [{single_result}]"
            )
            performance_data_per_kb_for_df[engine].append(runtime)
            performance_data_per_kb_for_df[f"{engine}_stats"].append(stat)
    return pd.DataFrame.from_dict(performance_data_per_kb_for_df)
