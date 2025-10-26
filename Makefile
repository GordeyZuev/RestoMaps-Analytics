.PHONY: up down logs notion reviews backup build restart status shell clean help lint format check

# Запуск
up:
	docker-compose up -d
	@echo "✅ Приложение запущено: http://localhost:8501"

# Остановка
down:
	docker-compose down

# Логи
logs:
	docker-compose logs -f app

# Синхронизация с Notion
notion:
	docker-compose exec app python main.py notion

# Парсинг отзывов
reviews:
	docker-compose exec app python main.py reviews

# Бэкап базы данных
backup:
	@mkdir -p backups
	@docker-compose exec -T postgres pg_dump -U postgres restomaps_analytics | gzip > backups/backup_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo "✅ Бэкап создан в backups/"

# Пересборка контейнеров
build:
	docker-compose build --no-cache
	@echo "✅ Контейнеры пересобраны"

# Перезапуск
restart:
	docker-compose restart
	@echo "✅ Сервисы перезапущены"

# Статус сервисов
status:
	@echo "📊 Статус сервисов:"
	docker-compose ps

# Подключение к контейнеру приложения
shell:
	docker-compose exec app /bin/bash

# Подключение к PostgreSQL
db:
	docker-compose exec postgres psql -U postgres -d restomaps_analytics

# Очистка Python кэша и временных файлов
clean:
	@echo "🧹 Очистка Python кэша и временных файлов..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.pyd" -delete 2>/dev/null || true
	find . -type f -name "*.so" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Python кэш и временные файлы очищены"

# Полная очистка Docker (контейнеры + volumes)
clean-docker:
	@echo "🐳 Очистка Docker контейнеров и volumes..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Docker контейнеры и volumes очищены"

# Очистка логов
clean-logs:
	@rm -rf logs/*.log
	@echo "✅ Логи очищены"

# Полный запуск с планировщиком
full:
	docker-compose exec app python main.py full

# Инициализация БД
init-db:
	docker-compose exec app python main.py init-db

# Просмотр использования ресурсов
stats:
	@echo "📈 Использование ресурсов:"
	docker stats --no-stream

# Обновление и перезапуск (для деплоя)
deploy: build up
	@echo "🚀 Деплой завершен"

# Линтинг и форматирование кода
lint:
	@echo "🔍 Запуск линтера Ruff..."
	python3 -m ruff check .
	@echo "✅ Линтинг завершен"

format:
	@echo "🎨 Форматирование кода..."
	python3 -m ruff format .
	@echo "✅ Форматирование завершено"

check: lint format
	@echo "✅ Проверка кода завершена"

# Справка
help:
	@echo "📋 Доступные команды:"
	@echo ""
	@echo "🚀 Основные:"
	@echo "  make up         - Запуск сервисов"
	@echo "  make down       - Остановка сервисов"
	@echo "  make restart    - Перезапуск сервисов"
	@echo "  make status     - Статус сервисов"
	@echo ""
	@echo "🔧 Управление:"
	@echo "  make build      - Пересборка контейнеров"
	@echo "  make clean      - Очистка Python кэша и временных файлов"
	@echo "  make clean-docker - Очистка Docker контейнеров и volumes"
	@echo "  make deploy     - Обновление и перезапуск"
	@echo ""
	@echo "💻 Разработка:"
	@echo "  make lint       - Проверка кода линтером"
	@echo "  make format     - Форматирование кода"
	@echo "  make check      - Линтинг + форматирование"
	@echo ""
	@echo "📊 Мониторинг:"
	@echo "  make logs       - Просмотр логов"
	@echo "  make stats      - Использование ресурсов"
	@echo "  make shell      - Подключение к контейнеру"
	@echo "  make db         - Подключение к PostgreSQL"
	@echo ""
	@echo "⚙️  Задачи:"
	@echo "  make notion     - Синхронизация с Notion"
	@echo "  make reviews    - Парсинг отзывов"
	@echo "  make full       - Запуск с планировщиком"
	@echo "  make init-db    - Инициализация БД"
	@echo "  make backup     - Бэкап БД"
	@echo ""
	@echo "🧹 Очистка:"
	@echo "  make clean      - Очистка Python кэша и временных файлов"
	@echo "  make clean-docker - Очистка Docker контейнеров и volumes"
	@echo "  make clean-logs - Очистка логов"

