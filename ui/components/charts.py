import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def render_weekly_ratings_chart(reviews_df: pd.DataFrame) -> pd.DataFrame | None:
    """Анализирует и отображает средние оценки по неделям."""
    if reviews_df.empty or "original_date" not in reviews_df.columns:
        return None

    valid_reviews = reviews_df[
        (reviews_df["original_date"].notna()) & (reviews_df["rating"].notna())
    ].copy()

    if valid_reviews.empty:
        return None

    valid_reviews["date"] = pd.to_datetime(
        valid_reviews["original_date"], errors="coerce"
    )
    valid_reviews = valid_reviews[valid_reviews["date"].notna()]

    if valid_reviews.empty:
        return None

    valid_reviews["year_week"] = valid_reviews["date"].dt.to_period("W")

    weekly_stats = (
        valid_reviews.groupby("year_week")
        .agg({"rating": ["mean", "count"], "date": ["min", "max"]})
        .round(2)
    )

    weekly_stats.columns = ["avg_rating", "review_count", "week_start", "week_end"]
    weekly_stats = weekly_stats.reset_index()
    weekly_stats["week_label"] = weekly_stats["year_week"].astype(str)

    return weekly_stats


def render_weekly_chart(weekly_data: pd.DataFrame) -> None:
    """Отображает график динамики оценок по неделям."""
    if weekly_data is None or weekly_data.empty:
        return

    weekly_data_sorted = weekly_data.sort_values("week_start")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=weekly_data_sorted["week_label"],
            y=weekly_data_sorted["avg_rating"],
            mode="lines+markers",
            name="Средняя оценка",
            line={"color": "#243071", "width": 3},
            marker={"size": 8, "color": "#243071"},
            hovertemplate=(
                "<b>%{x}</b><br>Средняя оценка: %{y:.2f}<br>"
                "Количество отзывов: %{customdata}<br><extra></extra>"
            ),
            customdata=weekly_data_sorted["review_count"],
        )
    )

    fig.update_layout(
        title="Динамика средних оценок по неделям",
        xaxis_title="Неделя",
        yaxis_title="Средняя оценка",
        yaxis={"range": [0, 5.5]},
        height=400,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"size": 12, "color": "#243071"},
        title_font={"size": 14, "color": "#243071"},
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
    )

    fig.update_xaxes(
        tickangle=45,
        showgrid=True,
        gridwidth=1,
        gridcolor="rgba(36, 48, 113, 0.2)",
        color="#243071",
    )
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor="rgba(36, 48, 113, 0.2)", color="#243071"
    )

    st.plotly_chart(fig, use_container_width=True)


def render_rating_distribution_chart(reviews_df: pd.DataFrame) -> None:
    """Отображает график распределения оценок."""
    if reviews_df.empty:
        st.info("📊 Нет данных об отзывах")
        return

    rating_counts = reviews_df["rating"].value_counts().sort_index()

    fig_hist = px.bar(
        x=rating_counts.index,
        y=rating_counts.values,
        title="Распределение оценок",
        labels={"x": "Оценка", "y": "Количество отзывов"},
        color_discrete_sequence=["#243071"],
    )
    fig_hist.update_layout(
        showlegend=False,
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"size": 12, "color": "#243071"},
        title_font={"size": 14, "color": "#243071"},
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
    )
    st.plotly_chart(fig_hist, use_container_width=True)


def render_analytics_charts(filtered_df: pd.DataFrame) -> None:
    """Отображает аналитические графики."""
    if filtered_df.empty:
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        city_counts = filtered_df["city"].fillna("—").value_counts().head(10)
        fig_cities = px.bar(
            x=city_counts.values,
            y=city_counts.index,
            orientation="h",
            title="Топ городов",
            labels={"x": "Количество мест", "y": "Город"},
            color_discrete_sequence=["#243071"],
        )
        fig_cities.update_layout(
            height=400,
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font={"size": 12, "color": "#243071"},
            title_font={"size": 14, "color": "#243071"},
            margin={"l": 0, "r": 0, "t": 40, "b": 0},
        )
        st.plotly_chart(fig_cities, use_container_width=True)

    with col2:
        ratings = filtered_df["yandex_rating"].dropna()
        if not ratings.empty:
            fig_ratings = px.histogram(
                x=ratings,
                nbins=20,
                title="Распределение рейтингов Яндекс.Карт",
                labels={"x": "Рейтинг", "y": "Количество мест"},
                color_discrete_sequence=["#243071"],
            )
            fig_ratings.update_layout(
                height=400,
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font={"size": 12, "color": "#243071"},
                title_font={"size": 14, "color": "#243071"},
                margin={"l": 0, "r": 0, "t": 40, "b": 0},
            )
            st.plotly_chart(fig_ratings, use_container_width=True)
        else:
            st.info("📊 Нет данных о рейтингах")

    with col3:
        place_types = filtered_df["place_type"].fillna("—").value_counts()
        fig_types = px.pie(
            values=place_types.values,
            names=place_types.index,
            title="Типы мест",
            color_discrete_sequence=[
                "#243071",
                "#4A90E2",
                "#7BB3F0",
                "#A8D0F0",
                "#C8E6F5",
            ],
        )
        fig_types.update_layout(
            height=400,
            showlegend=True,
            legend={
                "orientation": "h", "yanchor": "top", "y": -0.1,
                "xanchor": "center", "x": 0.5
            },
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font={"size": 12, "color": "#243071"},
            title_font={"size": 14, "color": "#243071"},
            margin={"l": 0, "r": 0, "t": 40, "b": 40},
        )
        st.plotly_chart(fig_types, use_container_width=True)
