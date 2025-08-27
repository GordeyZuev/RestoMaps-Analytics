import streamlit as st
import pandas as pd
from typing import Any, Optional


def render_metric(title: str, value: Any, scale: str = "") -> None:
    """Отображает метрику в стиле приложения"""
    display_value = f"{value:.1f}" if isinstance(value, (int, float)) and pd.notna(
        value) else str(value) if value is not None else "—"

    st.markdown(f"""
    <div class="stMetric">
        <div class="metric-title">{title}</div>
        <div class="metric-value">
            {display_value}<span class="rating-scale">{scale}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_rating_metric(title: str, rating: Optional[float], scale: str = "/10") -> None:
    """Отображает метрику рейтинга"""
    display_value = f"{rating:.1f}" if pd.notna(rating) else "—"

    st.markdown(f"""
    <div class="stMetric">
        <div class="metric-title">{title}</div>
        <div class="metric-value">
            {display_value}<span class="rating-scale">{scale}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_summary_metrics(restaurants_df: pd.DataFrame, filtered_df: pd.DataFrame) -> None:
    """Отображает основные метрики на главной странице"""
    col1, col2, col3 = st.columns(3)

    with col1:
        render_metric("Всего мест", int(len(restaurants_df)))

    with col2:
        visited_count = int(restaurants_df[restaurants_df["visited"]].shape[0]) if not restaurants_df.empty else 0
        render_metric("Посещенные", visited_count)

    with col3:
        avg_y_rating = (
            float(filtered_df["yandex_rating"].mean())
            if (not filtered_df.empty and filtered_df["yandex_rating"].notna().any())
            else 0.0
        )
        render_metric("Средний рейтинг (фильтр)", f"{avg_y_rating:.2f}")


def render_restaurant_metrics(restaurant_row: pd.Series) -> None:
    """Отображает метрики конкретного ресторана"""
    aa, bb = st.columns(2)

    my_avg = restaurant_row.get('my_avg_rating')
    yandex_rating = restaurant_row.get('yandex_rating')

    with aa:
        render_rating_metric("Мой средний балл", my_avg, "/10")

    with bb:
        render_rating_metric("Рейтинг Яндекс.Карт", yandex_rating, "/5")

    st.markdown("**Детальные оценки:**")
    e, f, g, h = st.columns(4)

    service_rating = restaurant_row.get('my_service_rating')
    food_rating = restaurant_row.get('my_food_rating')
    coffee_rating = restaurant_row.get('my_coffee_rating')
    interior_rating = restaurant_row.get('my_interior_rating')

    with e:
        render_rating_metric("Сервис", service_rating)
    with f:
        render_rating_metric("Еда", food_rating)
    with g:
        render_rating_metric("Кофе", coffee_rating)
    with h:
        render_rating_metric("Интерьер", interior_rating)


def render_restaurant_info(restaurant_row: pd.Series, reviews_df: pd.DataFrame) -> None:
    """Отображает информацию о ресторане"""
    st.markdown("**Основная статистика:**")
    a, b = st.columns(2)

    reviews_count = len(reviews_df) if not reviews_df.empty else 0

    last_review_date = "—"
    if not reviews_df.empty and 'original_date' in reviews_df.columns:
        last_review = reviews_df['original_date'].max()
        if pd.notna(last_review):
            last_review_date = last_review.strftime("%d.%m.%Y")

    with a:
        render_metric("Количество отзывов", reviews_count)

    with b:
        render_metric("Последний отзыв", last_review_date)
