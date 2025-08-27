import streamlit as st
import pandas as pd
from typing import List, Any


def render_sidebar_filters(restaurants_df: pd.DataFrame) -> dict:
    """Отображает фильтры в боковой панели"""
    st.sidebar.title("Фильтры")

    if st.sidebar.button("🔄 Обновить данные", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.divider()

    cities = sorted([c for c in restaurants_df["city"].dropna().unique().tolist()],
                    key=lambda x: len(x)) if not restaurants_df.empty else []
    selected_cities = st.sidebar.multiselect("Города", options=cities, default=cities[0] if cities else [])

    type_options = []
    if not restaurants_df.empty and "place_type" in restaurants_df.columns:
        type_options = sorted([t for t in restaurants_df["place_type"].dropna().unique().tolist()])
    selected_types = st.sidebar.multiselect("Типы мест", options=type_options, default=type_options)

    visited_mode = st.sidebar.selectbox(
        "Посещенность",
        options=["Все", "Только посещенные", "Только не посещенные"],
        index=0,
    )

    rating_range = st.sidebar.slider("Рейтинг Яндекс.Карт", min_value=0.0, max_value=5.0, value=(0.0, 5.0), step=0.1)

    unique_tags: List[str] = []
    if not restaurants_df.empty and "tags" in restaurants_df.columns:
        for tags in restaurants_df["tags"].dropna().tolist():
            if isinstance(tags, list):
                for t in tags:
                    if t not in unique_tags:
                        unique_tags.append(t)
    unique_tags = sorted(unique_tags)
    selected_tags = st.sidebar.multiselect("Теги", options=unique_tags)

    search_text = st.sidebar.text_input("Поиск по названию/комментарию")

    return {
        "cities": selected_cities,
        "types": selected_types,
        "visited_mode": visited_mode,
        "rating_range": rating_range,
        "tags": selected_tags,
        "search_text": search_text
    }


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Применяет фильтры к DataFrame"""
    if df.empty:
        return df

    filtered = df.copy()

    if filters["cities"]:
        filtered = filtered[filtered["city"].isin(filters["cities"])]

    if filters["visited_mode"] == "Только посещенные":
        filtered = filtered[filtered["visited"]]
    elif filters["visited_mode"] == "Только не посещенные":
        filtered = filtered[(filtered["visited"] == False) | (filtered["visited"].isna())]

    if filters["types"]:
        filtered = filtered[filtered["place_type"].isin(filters["types"])]

    if filters["tags"]:
        def has_all_tags(tags_value: Any) -> bool:
            if not isinstance(tags_value, list):
                return False
            return all(tag in tags_value for tag in filters["tags"])

        filtered = filtered[filtered["tags"].apply(has_all_tags)]

    if "yandex_rating" in filtered.columns:
        filtered = filtered[
            (filtered["yandex_rating"].fillna(0.0) >= filters["rating_range"][0])
            & (filtered["yandex_rating"].fillna(0.0) <= filters["rating_range"][1])
        ]

    if filters["search_text"].strip():
        q = filters["search_text"].strip().lower()
        name_match = filtered["name"].fillna("").str.lower().str.contains(q)
        comment_match = filtered["my_comment"].fillna("").str.lower().str.contains(q)
        filtered = filtered[name_match | comment_match]

    return filtered
