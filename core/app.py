import streamlit as st

from logger import logger
from ui.pages.dashboard import render_dashboard


def setup_page_config() -> None:
    """Настройка конфигурации страницы"""
    st.set_page_config(
        page_title="RestoMaps Analytics (beta)",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": None,
            "Report a bug": None,
            "About": "RestoMaps Analytics - Система анализа ресторанов и отзывов",
        },
    )


def setup_custom_styles() -> None:
    """Настройка пользовательских стилей"""
    st.markdown(
        """
    <style>
    /* Основные метрики */
    .stMetric {
        background-color: #f8f9fa !important;
        border: 1px solid #dee2e6 !important;
        border-radius: 12px !important;
        padding: 20px !important;
        margin: 10px 0 !important;
        box-shadow: 0 2px 8px rgba(36, 48, 113, 0.1) !important;
        transition: all 0.3s ease !important;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .stMetric:hover {
        box-shadow: 0 4px 12px rgba(36, 48, 113, 0.2) !important;
        transform: translateY(-2px) !important;
        border-color: #adb5bd !important;
    }

    /* Типографика */
    .metric-title {
        font-size: 0.8em;
        color: #666666;
        margin-bottom: 8px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.5em;
        font-weight: bold;
        color: #333333;
    }
    .rating-scale {
        color: #666666 !important;
        font-weight: 400 !important;
    }

    /* Теги и типы мест */
    .tag-container {
        display: inline-block;
        background-color: #243071;
        color: white;
        padding: 6px 12px;
        margin: 3px;
        border-radius: 15px;
        font-size: 0.9em;
        border: 1px solid #243071;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(36, 48, 113, 0.2);
    }
    .place-type-container {
        display: inline-block;
        background-color: #4A90E2;
        color: white;
        padding: 6px 12px;
        margin: 3px;
        border-radius: 15px;
        font-size: 0.9em;
        border: 1px solid #4A90E2;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(74, 144, 226, 0.2);
    }
    .stMetric .tag-container,
    .stMetric .place-type-container {
        margin: 1px;
        font-size: 0.8em;
        padding: 4px 8px;
        white-space: nowrap;
        flex-shrink: 0;
    }

    /* Кнопки Streamlit */
    .stButton > button {
        background-color: #f8f9fa;
        color: #333333;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #e9ecef;
        border-color: #adb5bd;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(173, 181, 189, 0.2);
    }

    /* Селекты и фильтры */
    .stSelectbox > div > div {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
    }
    .stSelectbox > div > div:focus-within {
        border-color: #adb5bd;
        box-shadow: 0 0 0 2px rgba(173, 181, 189, 0.1);
    }

    /* Заголовки */
    h1, h2, h3, h4, h5, h6 {
        color: #243071 !important;
    }

    /* Ссылки */
    a {
        color: #243071 !important;
    }
    a:hover {
        color: #4A90E2 !important;
    }

    /* Информационные блоки */
    .stAlert {
        border-left: 4px solid #243071;
        background-color: rgba(36, 48, 113, 0.05);
    }

    /* Таблицы */
    .stDataFrame {
        border: 1px solid #243071;
        border-radius: 8px;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def main() -> None:
    """Главная функция приложения"""
    setup_page_config()
    setup_custom_styles()

    # Инициализация логгера в session_state
    if "logger" not in st.session_state:
        st.session_state["logger"] = logger

    render_dashboard()


if __name__ == "__main__":
    main()
