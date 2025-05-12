from __future__ import annotations

import streamlit as st
from st_aggrid import AgGrid

from qlever.evaluation.data import (
    get_performance_comparison_per_kb_df,
    grid_options_for_comparison_df,
    remove_top_padding,
)
from qlever.evaluation.main import yaml_data

st.set_page_config(layout="wide")
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

kb = st.selectbox(
    label="Knowledge Graph",
    options=list(yaml_data.keys()),
)

df = get_performance_comparison_per_kb_df(yaml_data[kb])
AgGrid(
    df,
    gridOptions=grid_options_for_comparison_df(yaml_data[kb].keys()),
    height=700,
    allow_unsafe_jscode=True,
)
