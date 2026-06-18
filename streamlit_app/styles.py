from __future__ import annotations

import streamlit as st


def apply_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }
        [data-testid="stMetric"] {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 14px 16px;
        }
        [data-testid="stMetricLabel"] {
            color: #475569;
        }
        .section-note {
            color: #64748B;
            font-size: 0.95rem;
            margin-top: -0.4rem;
            margin-bottom: 0.8rem;
        }
        .source-box {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 12px 14px;
            color: #334155;
        }
        .modebar {
            display: none !important;
        }
        .stPlotlyChart {
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 8px 10px 2px 10px;
            background: #FFFFFF;
        }
        button[kind="primary"] {
            border-radius: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
