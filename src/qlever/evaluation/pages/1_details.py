from __future__ import annotations

import streamlit as st
from st_aggrid import AgGrid, AgGridReturn

from qlever.evaluation.data import (
    get_query_results_df,
    get_query_runtimes,
    grid_options_for_runtimes_df,
    remove_top_padding,
)
from qlever.evaluation.main import yaml_data

st.set_page_config("centered")
remove_top_padding()

st.title("SPARQL Engine Evaluation - Details")

col1, col2 = st.columns(2)

with col1:
    kb = st.selectbox(
        label="Knowledge Graph",
        options=list(yaml_data.keys()),
    )

with col2:
    engine_options = yaml_data.get(kb, [])
    if engine_options != []:
        engine_options = list(engine_options.keys())
    engine = st.selectbox(
        label="SPARQL Engine",
        options=engine_options,
    )

tab1, tab2, tab3, tab4 = st.tabs(
    ["Query Runtimes", "Full Query", "Execution Tree", "Query Results"]
)

with tab1:
    df = get_query_runtimes(yaml_data, kb, engine)

    selected_query = AgGrid(
        df,
        gridOptions=grid_options_for_runtimes_df(),
        height=600,
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
    st.header("Execution Tree")

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
            st.dataframe(df, hide_index=True, height=600)
