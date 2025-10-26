FROM python:3.11-slim

# Установка системных зависимостей для PostgreSQL и Selenium
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Настройка переменных окружения для Chrome
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Рабочая директория
WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем директорию для логов
RUN mkdir -p logs

# Порт для Streamlit
EXPOSE 8501

# Переменные окружения для Streamlit
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Команда запуска
CMD ["python", "main.py", "ui"]

