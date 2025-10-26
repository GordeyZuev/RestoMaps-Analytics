from typing import Any

import pandas as pd
from sqlalchemy import and_
import streamlit as st

from database.database import SessionLocal, init_db
from database.models import Restaurant
from logger import logger
from ui.components.charts import render_analytics_charts
from ui.components.filters import apply_filters, render_sidebar_filters
from ui.components.maps import render_map_section
from ui.components.metrics import render_summary_metrics


@st.cache_data(ttl=300, show_spinner=False)  # Обновление каждые 5 минут
def load_restaurants_df() -> pd.DataFrame:
    """Загружает данные ресторанов из базы данных."""
    session = get_db_session()
    db = session()
    try:
        restaurants: list[Restaurant] = (
            db.query(Restaurant)
            .filter(
                and_(
                    Restaurant.address.isnot(None),
                    Restaurant.address != "",
                    Restaurant.latitude.isnot(None),
                    Restaurant.longitude.isnot(None),
                )
            )
            .all()
        )
        records: list[dict[str, Any]] = []
        for r in restaurants:
            personal_ratings = [
                v
                for v in [
                    r.my_service_rating,
                    r.my_food_rating,
                    r.my_coffee_rating,
                    r.my_interior_rating,
                ]
                if v is not None
            ]
            my_avg_rating = (
                round(sum(personal_ratings) / len(personal_ratings), 2)
                if personal_ratings
                else None
            )

            # Собираем все processed_tags из отзывов ресторана и считаем их частоту
            tag_counts = {}
            for review in r.reviews:
                if review.processed_tags:
                    for tag in review.processed_tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1

            # Берем 4 самых популярных тега
            top_processed_tags = sorted(
                tag_counts.items(), key=lambda x: x[1], reverse=True
            )[:4]
            unique_processed_tags = [tag for tag, count in top_processed_tags]

            records.append(
                {
                    "id": r.id,
                    "notion_id": r.notion_id,
                    "name": r.name,
                    "place_type": r.place_type,
                    "city": r.city,
                    "address": r.address,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "yandex_rating": r.yandex_rating,
                    "visited": bool(r.visited) if r.visited is not None else False,
                    "my_service_rating": r.my_service_rating,
                    "my_food_rating": r.my_food_rating,
                    "my_coffee_rating": r.my_coffee_rating,
                    "my_interior_rating": r.my_interior_rating,
                    "my_avg_rating": my_avg_rating,
                    "tags": r.tags or [],
                    "processed_tags": unique_processed_tags,
                    "my_comment": r.my_comment,
                    "yandex_maps_url": r.yandex_maps_url,
                    "last_updated": r.last_updated,
                    "created_at": r.created_at,
                }
            )
        df = pd.DataFrame.from_records(records)
        if df.empty:
            df = pd.DataFrame(
                columns=[
                    "id",
                    "notion_id",
                    "name",
                    "place_type",
                    "city",
                    "address",
                    "latitude",
                    "longitude",
                    "yandex_rating",
                    "visited",
                    "my_service_rating",
                    "my_food_rating",
                    "my_coffee_rating",
                    "my_interior_rating",
                    "my_avg_rating",
                    "tags",
                    "processed_tags",
                    "my_comment",
                    "yandex_maps_url",
                    "last_updated",
                    "created_at",
                ]
            )
        return df
    finally:
        db.close()


@st.cache_resource
def get_db_session():
    """Получает сессию базы данных."""
    logger.info("Инициализация базы данных")
    init_db()
    return SessionLocal


def render_dashboard() -> None:
    if "auto_select_first" not in st.session_state:
        st.session_state["auto_select_first"] = True

    restaurants_df = load_restaurants_df()

    filters = render_sidebar_filters(restaurants_df)
    filtered_df = apply_filters(restaurants_df, filters)

    st.title("RestoMaps Analytics — Мои места")

    render_summary_metrics(restaurants_df, filtered_df)

    st.divider()

    render_map_section(filtered_df)

    st.subheader("Детали и отзывы")
    render_restaurant_selector(filtered_df)

    st.subheader("Таблица мест")
    render_restaurants_table(filtered_df)

    st.divider()

    st.subheader("📊 Аналитика по фильтрам")
    render_analytics_charts(filtered_df)

    st.caption("RestoMaps Analytics (by Gordey)")


def render_restaurant_selector(filtered_df: pd.DataFrame) -> None:
    """Отображает селектор ресторана и детали."""
    selected_row = None
    selected_place_id = st.session_state.get("selected_place_id")
    if selected_place_id and not filtered_df.empty and "id" in filtered_df.columns:
        sel_row = filtered_df[filtered_df["id"] == selected_place_id].head(1)
        if not sel_row.empty:
            selected_row = sel_row.iloc[0]

    selected_name = None
    if not filtered_df.empty:
        names = sorted(filtered_df["name"].tolist())

        current_index = 0
        if selected_row is not None and "name" in selected_row:
            try:
                current_index = names.index(selected_row["name"]) + 1  # +1 из-за "—"
            except ValueError:
                current_index = 0
        else:
            # Если ничего не выбрано, автоматически выбираем первое место
            if names and st.session_state.get("auto_select_first", True):
                current_index = 1  # Выбираем первое место (индекс 1, так как 0 это "—")
                st.session_state["auto_select_first"] = False

        selected_name = st.selectbox(
            "Выберите место",
            options=["—", *names],
            index=current_index,
            key="place_select_name",
        )

    if selected_name and selected_name != "—":
        sel_row = filtered_df[filtered_df["name"] == selected_name].head(1)
        if not sel_row.empty:
            selected_row = sel_row.iloc[0]
            if "id" in sel_row.columns:
                new_id = int(sel_row.iloc[0]["id"])
                if st.session_state.get("selected_place_id") != new_id:
                    st.session_state["selected_place_id"] = new_id

    if selected_row is not None:
        from ui.pages.restaurant_detail import render_restaurant_detail

        render_restaurant_detail(selected_row)
    else:
        st.caption(
            "Наведите на точку на карте или выберите из списка, чтобы увидеть детали"
        )


def render_restaurants_table(filtered_df: pd.DataFrame) -> None:
    """Отображает таблицу ресторанов."""
    display_cols = [
        "id",
        "name",
        "city",
        "place_type",
        "yandex_rating",
        "my_avg_rating",
        "visited",
        "my_service_rating",
        "my_food_rating",
        "my_coffee_rating",
        "my_interior_rating",
        "tags",
        "processed_tags",
        "address",
    ]
    existing_display_cols = [c for c in display_cols if c in filtered_df.columns]
    table_df = (
        filtered_df[existing_display_cols]
        .sort_values(by=["city", "name"], na_position="last")
        .copy()
    )
    st.dataframe(
        table_df.drop(columns=["id"]) if "id" in table_df.columns else table_df,
        use_container_width=True,
        height=420,
    )
