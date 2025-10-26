# 🚀 Deployment Guide

## Быстрая установка в Docker

### 1. Подготовка системы

#### Ubuntu/Debian
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker и Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo usermod -aG docker $USER

# Перезагрузка
sudo reboot
```

#### macOS
```bash
# Установка через Homebrew
brew install docker docker-compose
```

### 2. Клонирование проекта

```bash
# Клонирование репозитория
git clone https://github.com/your-username/RestoMaps-Analytics.git
cd RestoMaps-Analytics
```

### 3. Настройка конфигурации

```bash
# Создание файла конфигурации
cp env.example config/.env

# Редактирование конфигурации
nano config/.env
```

#### Обязательные настройки в config/.env:
```bash
# База данных
POSTGRES_USER=restomaps_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=restomaps_analytics

# Notion API (обязательно)
NOTION_API_KEY=secret_your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id

# Яндекс API (опционально)
YA_GEO_CODER_API_KEY=your_yandex_api_key

# Логирование
LOG_LEVEL=INFO
```

### 4. Получение API ключей

#### Notion API
1. Перейдите на [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Нажмите "New integration"
3. Заполните название (например, "RestoMaps Analytics")
4. Скопируйте "Internal Integration Token"
5. Добавьте интеграцию к базе данных Notion (Share → Invite)

#### Яндекс API (опционально)
1. Перейдите на [https://developer.tech.yandex.ru/](https://developer.tech.yandex.ru/)
2. Создайте проект и получите API ключ

### 5. Запуск проекта

```bash
# Запуск через Docker Compose
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f app
```

### 6. Первый запуск

```bash
# 1. Первоначальная синхронизация с Notion (обязательно)
docker-compose exec app python main.py --notion

# 2. Парсинг отзывов (опционально)
docker-compose exec app python main.py --reviews

# 3. Откройте в браузере
# http://localhost:8501
```

## Полезные команды

### Основные команды
```bash
# Запуск
make up

# Остановка
make down

# Перезапуск
make restart

# Просмотр логов
make logs

# Статус сервисов
make status
```

### Управление данными
```bash
# Синхронизация с Notion
make notion

# Парсинг отзывов
make reviews

# NLP обработка
make nlp

# Бэкап БД
make backup

# Подключение к контейнеру
make shell
```

### Обновление проекта
```bash
# Остановка
docker-compose down

# Обновление кода
git pull origin main

# Проверка качества кода (Ruff)
make check

# Пересборка и запуск
docker-compose build --no-cache
docker-compose up -d

# Проверка
docker-compose logs -f app
```

## Настройка автоматических задач

### Запуск с планировщиком
```bash
# Запуск планировщика в отдельном контейнере
docker-compose exec app python main.py --scheduler

# Или запуск с UI + планировщик
docker-compose exec app python main.py --full
```

### Настройка бэкапов
```bash
# Автоматические бэкапы через cron
./backup.sh setup-cron

# Ручной бэкап
./backup.sh backup

# Просмотр бэкапов
./backup.sh list
```

## Разработка

### Команды разработки
```bash
# Проверка качества кода
make lint        # Линтинг с помощью Ruff
make format      # Форматирование кода с помощью Ruff
make check       # Полная проверка (линтинг + форматирование)

# Отладка
make shell       # Подключение к контейнеру для отладки
```

### Click CLI команды
```bash
# Прямой запуск команд через Click
python main.py --help                    # Справка по командам
python main.py ui                        # Запуск веб-интерфейса
python main.py notion                    # Синхронизация с Notion
python main.py reviews                   # Парсинг отзывов
python main.py init-db                   # Инициализация БД
python main.py scheduler                 # Запуск планировщика
python main.py check-failed              # Повторная проверка ресторанов с ошибками
```

### Ruff конфигурация
```bash
# Проверка конкретного файла
ruff check parsers/ya_maps_reviews_parser.py

# Автоисправление ошибок
ruff check --fix .

# Форматирование с проверкой
ruff format --check .
```

## Устранение неполадок

### Перезапуск при проблемах
```bash
# Полный перезапуск
docker-compose down
docker-compose up -d

# Очистка и перезапуск
docker-compose down -v
docker-compose up -d
```

### Логи и отладка
```bash
# Логи приложения
docker-compose logs app

# Логи базы данных
docker-compose logs postgres

# Подключение к контейнеру для отладки
docker-compose exec app bash
```

## Структура проекта

```
RestoMaps-Analytics/
├── config/
│   └── .env                 # Конфигурация
├── database/
│   ├── models.py           # Модели данных
│   ├── crud.py             # CRUD операции
│   └── database.py         # Подключение к БД
├── ui/
│   ├── pages/              # Страницы приложения
│   └── components/         # UI компоненты
├── jobs/                   # Автоматические задачи
├── docker-compose.yml      # Docker конфигурация
├── Dockerfile             # Docker образ
├── main.py                # Точка входа
├── Makefile               # Команды управления
└── backup.sh              # Скрипт бэкапов
```

**Документация:**
- [README.md](README.md) — описание проекта
- [TECHNICAL.md](TECHNICAL.md) — техническая документация