from __future__ import annotations

import streamlit as st

from qlever.evaluation.data import (
    get_all_query_stats_by_kb,
    remove_top_padding,
    yaml_data,
)

st.set_page_config(page_title="SPARQL Engine Performance Evaluation")
remove_top_padding()

st.title("SPARQL Engine Comparison")

if not yaml_data:
    st.error("No Knowledge Graphs or SPARQL Engines data available!")
    st.markdown(
        "Make sure you called the `serve-evaluation-app` with the correct `--results-dir`"
    )
    st.stop()

for kb in yaml_data:
    st.write(f"### {kb.capitalize()}")
    df = get_all_query_stats_by_kb(yaml_data, kb)
    st.dataframe(
        df,
        hide_index=True,
        column_config={
            "engine_name": "SPARQL Engine",
            "failed": st.column_config.NumberColumn(
                "Failed",
                format="%.2f%%",
            ),
            "gmeanTime": st.column_config.NumberColumn(
                "Geometric Mean",
                format="%.2fs",
            ),
            "ameanTime": st.column_config.NumberColumn(
                "Arithmetic Mean",
                format="%.2fs",
            ),
            "medianTime": st.column_config.NumberColumn(
                "Median",
                format="%.2fs",
            ),
            "under1s": st.column_config.NumberColumn(
                "<= 1s",
                format="%.2f%%",
            ),
            "between1to5s": st.column_config.NumberColumn(
                "(1s, 5s]",
                format="%.2f%%",
            ),
            "over5s": st.column_config.NumberColumn(
                "> 5s",
                format="%.2f%%",
            ),
        },
    )
