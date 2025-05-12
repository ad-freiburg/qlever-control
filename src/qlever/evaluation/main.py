from __future__ import annotations

import requests
import streamlit as st

from qlever.evaluation.data import (
    get_all_query_stats_by_kb,
    remove_top_padding,
)

# Fetch data from API
url = "http://localhost:8000/yaml_data"
response = requests.get(url)
yaml_data = response.json()

st.set_page_config("centered")
remove_top_padding()

st.title("SPARQL Engine Comparison")

for kb in yaml_data:
    st.write(f"### {kb.capitalize()}")
    df = get_all_query_stats_by_kb(yaml_data, kb)
    st.dataframe(df, hide_index=True)