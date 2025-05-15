from __future__ import annotations

import re

import streamlit as st
from graphviz import Graph
from st_aggrid import AgGrid, AgGridReturn

from qlever.evaluation.data import (
    build_graph_treant_style,
    get_query_results_df,
    get_query_runtimes,
    grid_options_for_runtimes_df,
    remove_top_padding,
    yaml_data,
)

st.set_page_config(page_title="Query Details", layout="centered")
remove_top_padding()

# st.title("SPARQL Engine Evaluation - Details")

# col1, col2 = st.columns(2)

with st.sidebar:
    kb_options = list(yaml_data.keys()) if yaml_data else []
    # try:
    #     kb_idx_from_url_params = kb_options.index(st.query_params["kb"])
    # except (ValueError, KeyError):
    # kb_idx_from_url_params = 0
    kb = st.selectbox(
        label="Knowledge Graph",
        options=kb_options,
        # index=kb_idx_from_url_params,
    )
    # st.query_params["kb"] = kb

with st.sidebar:
    engine_options = yaml_data.get(kb, [])
    if engine_options != [] and isinstance(engine_options, dict):
        engine_options = list(engine_options.keys())
    else:
        engine_options = []
    # try:
    #     engine_idx_from_url_params = engine_options.index(st.query_params["engine"])
    # except (ValueError, KeyError):
    # engine_idx_from_url_params = 0
    engine = st.selectbox(
        label="SPARQL Engine",
        options=engine_options,
        # index=engine_idx_from_url_params,
    )
    # st.query_params["engine"] = engine

if not all([kb, engine]):
    st.title("Engine Query Details")
    st.error("No Knowledge Graphs or SPARQL Engines data available!")
    st.markdown(
        "Make sure you called the `serve-evaluation-app` with the correct `--results-dir`"
    )
    st.stop()

engine_title = engine.capitalize()
if "qlever" in engine.lower():
    engine_title = re.sub(r"qlever", "QLever", engine, flags=re.IGNORECASE)
title_str = f"{engine_title} ({kb})"
st.title(f"{title_str} Details")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Query Runtimes", "Full Query", "Execution Tree", "Query Results"]
)

with tab1:
    df = get_query_runtimes(yaml_data, kb, engine)

    selected_query = AgGrid(
        df,
        gridOptions=grid_options_for_runtimes_df(),
        height=700,
        allow_unsafe_jscode=True,
    )


def get_selected_query_idx(
    selected_query: AgGridReturn,
) -> int | None:
    if selected_query.selected_rows is None:
        return None
    return int(selected_query.selected_rows_id[0])


with tab2:
    selected_query_idx = get_selected_query_idx(selected_query)
    if selected_query_idx is None:
        st.write("Please select a query from the Query runtimes table!")
    else:
        full_query = yaml_data[kb][engine]["queries"][selected_query_idx][
            "sparql"
        ]
        st.code(body=full_query, language="sparql")

with tab3:
    queries = yaml_data[kb][engine]["queries"]
    has_exec_tree = False
    for query in queries:
        if not isinstance(query["results"], str):
            if query["runtime_info"].get("query_execution_tree") is not None:
                has_exec_tree = True
    if not has_exec_tree:
        st.write(
            "Execution tree is only available for QLever with qlever-results+json format!"
        )
    else:
        selected_query_idx = get_selected_query_idx(selected_query)
        if selected_query_idx is None:
            st.write("Please select a query from the Query runtimes table!")
        else:
            query_tree = yaml_data[kb][engine]["queries"][selected_query_idx][
                "runtime_info"
            ]["query_execution_tree"]

            dot = Graph(format="svg")
            dot.attr(rankdir="BT")  # Bottom to top
            dot = build_graph_treant_style(query_tree, dot)
            st.graphviz_chart(dot, use_container_width=False)

with tab4:
    selected_query_idx = get_selected_query_idx(selected_query)
    if selected_query_idx is None:
        st.write("Please select a query from the Query runtimes table!")
    else:
        query = yaml_data[kb][engine]["queries"][selected_query_idx]
        if isinstance(query["results"], str):
            st.write(
                f"#### Query failed in {round(query['runtime_info']['client_time'], 2)} s"
            )
            st.write(query["results"])
        else:
            df = get_query_results_df(query["headers"], query["results"])
            st.dataframe(df, hide_index=True, height=700)
