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

st.title("Performance Comparison")

st.markdown(
    """
    <style>
        .custom-tooltip {
            white-space: pre-wrap;
            font-family: monospace;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    kb_options = list(yaml_data.keys())
    # try:
    #     kb_idx_from_url_params = kb_options.index(st.query_params["kb"])
    # except (ValueError, KeyError):
    kb_idx_from_url_params = 0

    kb = st.selectbox(
        label="Knowledge Graph",
        options=kb_options,
        index=kb_idx_from_url_params,
    )
    # st.query_params["kb"] = kb

with col2:
    engines_to_hide = st.multiselect(
        label="Engines to hide",
        options=list(yaml_data[kb].keys()),
    )

df = get_performance_comparison_per_kb_df(yaml_data[kb])
AgGrid(
    df,
    gridOptions=grid_options_for_comparison_df(
        yaml_data[kb].keys(), engines_to_hide
    ),
    height=700,
    allow_unsafe_jscode=True,
)
