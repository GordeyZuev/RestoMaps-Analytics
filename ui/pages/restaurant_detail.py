import pandas as pd
import streamlit as st

from database.database import SessionLocal, init_db
from database.models import Review
from logger import logger
from ui.components.charts import (
    render_rating_distribution_chart,
    render_weekly_chart,
    render_weekly_ratings_chart,
)
from ui.components.metrics import render_restaurant_info, render_restaurant_metrics


@st.cache_data(show_spinner=False)
def load_reviews_df(restaurant_id: int) -> pd.DataFrame:
    """Загружает отзывы для конкретного ресторана."""
    session = get_db_session()
    db = session()
    try:
        reviews = (
            db.query(Review)
            .filter(Review.restaurant_id == restaurant_id)
            .order_by(Review.original_date.desc().nullslast())
            .all()
        )
        records = []
        for rv in reviews:
            records.append(
                {
                    "id": rv.id,
                    "author": rv.author_name,
                    "rating": rv.rating,
                    "text": rv.comment_text,
                    "original_date": rv.original_date,
                    "retrieved_date": rv.retrieved_date,
                    "processed_verdict": rv.processed_verdict,
                    "processed_tags": rv.processed_tags or [],
                }
            )
        return pd.DataFrame.from_records(records)
    finally:
        db.close()


@st.cache_resource
def get_db_session():
    """Получает сессию базы данных."""
    logger.info("Инициализация базы данных")
    init_db()
    return SessionLocal


def render_restaurant_detail(restaurant_row: pd.Series) -> None:
    """Отображает детальную информацию о ресторане."""
    st.markdown(f"## Анализ места: :red-background[{restaurant_row['name']}]")

    render_place_info(restaurant_row)

    reviews_df = load_reviews_df(int(restaurant_row["id"]))
    render_restaurant_metrics(restaurant_row)
    render_restaurant_info(restaurant_row, reviews_df)

    render_place_details(restaurant_row)
    render_my_comment(restaurant_row)
    render_restaurant_charts(reviews_df)
    render_reviews_section(reviews_df)


def render_place_info(restaurant_row: pd.Series) -> None:
    """Отображает информацию о типе места и тегах."""
    place_type = restaurant_row.get("place_type", "")
    tags = restaurant_row.get("tags", [])
    processed_tags = restaurant_row.get("processed_tags", [])

    info_content = ""
    if (
        place_type
        or (isinstance(tags, list) and tags)
        or (isinstance(processed_tags, list) and processed_tags)
    ):
        info_content += '<div class="stMetric">'
        info_content += (
            '<div style="display: flex; flex-wrap: wrap; gap: 2px; '
            'align-items: center; justify-content: flex-start;">'
        )

        if place_type:
            info_content += f'<span class="place-type-container">{place_type}</span>'

        if isinstance(tags, list) and tags:
            for tag in tags:
                info_content += f'<span class="tag-container">{tag}</span>'

        if isinstance(processed_tags, list) and processed_tags:
            for tag in processed_tags:
                info_content += (
                    f'<span class="tag-container" '
                    f'style="background-color: #e8f5e9; color: #2e7d32; '
                    f'border: 1px solid #66bb6a;">{tag}</span>'
                )

        info_content += "</div>"
        info_content += "</div>"

    if info_content:
        st.markdown(info_content, unsafe_allow_html=True)


def render_place_details(restaurant_row: pd.Series) -> None:
    """Отображает детальную информацию о месте."""
    st.markdown(" ")
    st.markdown("**Информация о месте:**")
    info_col1, info_col2 = st.columns(2)

    with info_col1:
        st.markdown(f"**Адрес:** {restaurant_row.get('address', '—')}")

    with info_col2:
        if restaurant_row.get("yandex_maps_url"):
            st.link_button(
                "🔗 Открыть на Яндекс.Картах", restaurant_row["yandex_maps_url"]
            )


def render_my_comment(restaurant_row: pd.Series) -> None:
    """Отображает мой комментарий."""
    my_comment = restaurant_row.get("my_comment", "")
    if my_comment and my_comment.strip():
        st.markdown(" ")
        st.markdown("**Мой комментарий:**")
        st.info(my_comment)


def render_restaurant_charts(reviews_df: pd.DataFrame) -> None:
    """Отображает графики для ресторана."""
    st.markdown(" ")
    weekly_data = render_weekly_ratings_chart(reviews_df)

    if weekly_data is not None and not weekly_data.empty:
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            render_weekly_chart(weekly_data)

        with chart_col2:
            render_rating_distribution_chart(reviews_df)

        render_weekly_metrics(weekly_data)
    else:
        st.caption("Недостаточно данных для анализа по неделям")
        render_rating_distribution_chart(reviews_df)


def render_weekly_metrics(weekly_data: pd.DataFrame) -> None:
    """Отображает метрики по неделям."""
    if len(weekly_data) > 1:
        st.markdown(" ")
        col1, col2 = st.columns(2)
        with col1:
            trend = (
                "📈 Растет"
                if weekly_data["avg_rating"].iloc[-1]
                > weekly_data["avg_rating"].iloc[0]
                else "📉 Падает"
            )
            st.markdown(
                f"""
            <div class="stMetric">
                <div class="metric-title">Тренд оценки</div>
                <div class="metric-value">{trend}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with col2:
            avg_reviews_per_week = weekly_data["review_count"].mean()
            st.markdown(
                f"""
            <div class="stMetric">
                <div class="metric-title">Среднее количество отзывов за неделю</div>
                <div class="metric-value">{avg_reviews_per_week:.1f}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )


def render_reviews_section(reviews_df: pd.DataFrame) -> None:
    """Отображает секцию с отзывами."""
    st.markdown(" ")
    st.markdown("**Отзывы:**")
    if reviews_df.empty:
        st.caption("Отзывы не найдены")
    else:
        st.dataframe(
            reviews_df[
                [
                    c
                    for c in [
                        "original_date",
                        "author",
                        "rating",
                        "text",
                        "processed_verdict",
                        "processed_tags",
                    ]
                    if c in reviews_df.columns
                ]
            ].head(50),
            use_container_width=True,
            height=350,
        )
