from __future__ import annotations

import streamlit as st
from st_aggrid import AgGrid

from qlever.evaluation.data import (
    get_performance_comparison_per_kb_df,
    grid_options_for_comparison_df,
    remove_top_padding,
    yaml_data,
)

st.set_page_config(
    page_title="SPARQL Engine Performance Comparison", layout="wide"
)
remove_top_padding()


# col1, col2, col3 = st.columns([5, 5, 2], vertical_alignment="bottom")

with st.sidebar:
    kb_options = list(yaml_data.keys()) if yaml_data else []
    # try:
    #     kb_idx_from_url_params = kb_options.index(st.query_params["kb"])
    # except (ValueError, KeyError):
    if "comparison_kb" not in st.session_state:
        kb_idx = 0
    else:
        kb_idx = kb_options.index(st.session_state.comparison_kb)

    kb = st.selectbox(
        label="Knowledge Graph",
        options=kb_options,
        index=kb_idx,
    )
    # st.query_params["kb"] = kb

with st.sidebar:
    engine_options = yaml_data.get(kb, [])
    if engine_options != [] and isinstance(engine_options, dict):
        engine_options = list(engine_options.keys())
    else:
        engine_options = []
    engines_to_hide = st.multiselect(
        label="Engines to hide",
        options=engine_options,
    )

with st.sidebar:
    show_result_size = st.checkbox("Show result size")

if kb is None:
    st.error("No Knowledge Graphs data available!")
    st.markdown(
        "Make sure you called the `serve-evaluation-app` with the correct `--results-dir`"
    )
    st.stop()

st.title(f"Performance comparison for {kb.capitalize()}")

df = get_performance_comparison_per_kb_df(yaml_data[kb])
response = AgGrid(
    df,
    gridOptions=grid_options_for_comparison_df(
        yaml_data[kb].keys(), engines_to_hide, show_result_size
    ),
    height=750,
    allow_unsafe_jscode=True,
)
