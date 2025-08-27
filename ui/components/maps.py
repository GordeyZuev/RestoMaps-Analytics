import streamlit as st
import pandas as pd
import pydeck as pdk
import folium
from math import hypot
from typing import Optional

from streamlit_folium import st_folium


def type_to_color_hex(place_type: str) -> str:
    """Возвращает цвет для типа места"""
    t = (place_type or "").strip().lower()
    if t in ("restaurant", "ресторан"):
        return "#FF6347"
    if t in ("cafe", "кафе"):
        return "#1E90FF"
    if t in ("bakery", "пекарня"):
        return "#FFD700"
    if t in ("bar", "бар"):
        return "#BA55D3"
    return "#A0A0A0"


def type_to_color_rgb(place_type: str):
    """Возвращает RGB цвет для типа места"""
    t = (place_type or "").strip().lower()
    if t in ("restaurant", "ресторан"):
        return [255, 99, 71]
    if t in ("cafe", "кафе"):
        return [30, 144, 255]
    if t in ("bakery", "пекарня"):
        return [255, 215, 0]
    if t in ("bar", "бар"):
        return [186, 85, 211]
    return [160, 160, 160]


def render_folium_map(map_df: pd.DataFrame, selected_place_id: Optional[int] = None) -> None:
    """Отображает карту с помощью Folium"""
    try:
        # Используем фиксированный центр - НЕ перемещаем карту при выборе места
        center = [float(map_df["latitude"].mean()), float(map_df["longitude"].mean())]

        fmap = folium.Map(location=center, zoom_start=12, tiles="CartoDB Positron No Labels")

        for _, r in map_df.iterrows():
            color_hex = type_to_color_hex(r.get("place_type"))

            # Формируем теги с цветовым выделением
            tags_html = ""
            if r.get('tags'):
                tags_html += f"<span style='color: #1E90FF;'>Теги: {', '.join(r.get('tags'))}</span>"

            processed_tags_html = ""
            if r.get('processed_tags'):
                if tags_html:
                    processed_tags_html += "<br/>"
                processed_tags_html += f"<span style='color: #32CD32;'>Обработанные: {
                    ', '.join(
                        r.get('processed_tags'))}</span>"

            yandex_rating = r.get('yandex_rating')
            yandex_rating_str = f"{yandex_rating:.1f}" if yandex_rating is not None else "—"

            tooltip_html = (
                f"<b>{r.get('name')}</b><br/>{r.get('city') or ''}<br/>"
                f"Тип: {r.get('place_type') or '—'}<br/>"
                f"Моя ср.: {r.get('my_avg_rating') or '—'} | Я.Карты: {yandex_rating_str}<br/>"
                f"{tags_html}{processed_tags_html}"
            )
            folium.CircleMarker(
                location=[r["latitude"], r["longitude"]],
                radius=6,
                color=color_hex,
                fill=True,
                fill_color=color_hex,
                fill_opacity=0.95,
                tooltip=tooltip_html,
                popup=r.get("name", ""),
            ).add_to(fmap)

        if selected_place_id is not None and "id" in map_df.columns:
            sel_row = map_df[map_df["id"] == selected_place_id].head(1)
            if not sel_row.empty:
                sr = sel_row.iloc[0]
                folium.CircleMarker(
                    location=[sr["latitude"], sr["longitude"]],
                    radius=10,
                    color="#000000",
                    weight=2,
                    fill=False,
                    opacity=0.9,
                ).add_to(fmap)

        # Используем стабильный ключ, чтобы карта не перерисовывалась полностью
        # Ключ зависит только от количества точек (меняется при изменении фильтров)
        ret = st_folium(fmap, height=500, use_container_width=True, key=f"map_{len(map_df)}")

        if ret and ret.get("last_object_clicked"):
            lat = ret["last_object_clicked"].get("lat")
            lon = ret["last_object_clicked"].get("lng")
            if lat is not None and lon is not None:
                best_id = None
                best_dist = 1e9
                for _, r in map_df.iterrows():
                    d = hypot(float(r["latitude"]) - float(lat), float(r["longitude"]) - float(lon))
                    if d < best_dist:
                        best_dist = d
                        best_id = int(r["id"]) if pd.notna(r.get("id")) else None
                if best_id:
                    st.session_state["selected_place_id"] = best_id

        render_map_legend()

    except Exception:
        render_pydeck_map(map_df, selected_place_id)


def render_pydeck_map(map_df: pd.DataFrame, selected_place_id: Optional[int] = None) -> None:
    """Отображает карту с помощью PyDeck (fallback)"""

    mp = map_df.rename(columns={"latitude": "lat", "longitude": "lon"}).copy()
    mp["color"] = mp["place_type"].apply(type_to_color_rgb)
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=mp,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_radius=60,
        pickable=True,
        stroked=False,
        radius_min_pixels=3,
        radius_max_pixels=18,
    )
    tooltip = {
        "html": "<b>{name}</b><br/>{city}<br/>Тип: {place_type}<br/>Моя ср.: {my_avg_rating} | Я.Карты: {yandex_rating}<br/>Теги: {tags}<br/>Обработанные: {processed_tags}",
        "style": {
            "backgroundColor": "#111",
            "color": "#fff"},
    }
    midpoint = [float(mp["lat"].mean()), float(mp["lon"].mean())]
    view_state = pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=11)
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="mapbox://styles/mapbox/light-v11")
    st.pydeck_chart(deck, use_container_width=True)
    render_map_legend()


def render_map_legend() -> None:
    """Отображает легенду карты"""
    st.markdown(
        """
        <div style='margin-top:6px; display:flex; flex-wrap:wrap; gap:24px; align-items:center; font-size:12px; color:#333;'>
          <div style='display:flex; align-items:center; gap:8px;'><span style='width:10px;height:10px;border-radius:50%;background:#FF6347;display:inline-block;'></span>Ресторан</div>
          <div style='display:flex; align-items:center; gap:8px;'><span style='width:10px;height:10px;border-radius:50%;background:#1E90FF;display:inline-block;'></span>Кафе</div>
          <div style='display:flex; align-items:center; gap:8px;'><span style='width:10px;height:10px;border-radius:50%;background:#FFD700;display:inline-block;'></span>Пекарня</div>
          <div style='display:flex; align-items:center; gap:8px;'><span style='width:10px;height:10px;border-radius:50%;background:#BA55D3;display:inline-block;'></span>Бар</div>
          <div style='display:flex; align-items:center; gap:8px;'><span style='width:10px;height:10px;border-radius:50%;background:#A0A0A0;display:inline-block;'></span>Другое</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_map_section(filtered_df: pd.DataFrame) -> None:
    """Отображает секцию с картой"""
    st.subheader("Карта")
    map_container = st.container()

    with map_container:
        map_df = filtered_df.dropna(subset=["latitude", "longitude"]).copy() if not filtered_df.empty else filtered_df
        if not map_df.empty:
            selected_place_id = st.session_state.get("selected_place_id")
            render_folium_map(map_df, selected_place_id)
        else:
            st.caption("Нет данных для отображения на карте")
