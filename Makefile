# AI Personal BI Assistant Makefile

.PHONY: help start stop restart db api worker frontend init

help:
	@echo "Available commands:"
	@echo "  make start    - Start everything (Docker, DB init, API, Worker, Frontend)"
	@echo "  make stop     - Stop everything (Docker, API, Worker, Frontend)"
	@echo "  make restart  - Stop, wait 1s, and start everything again"
	@echo "  make init     - Initialize database and seed data"
	@echo "  make api      - Run FastAPI backend only"
	@echo "  make worker   - Run Celery worker only"
	@echo "  make frontend - Run React frontend only"

restart: stop
	@sleep 1
	$(MAKE) start

start:
	@echo "🚀 [1/4] Starting Infrastructure (Postgres, Redis)..."
	docker compose up -d db redis
	@echo "⏳ Waiting for database to be ready..."
	@sleep 3
	@echo "📦 [2/4] Initializing Database..."
	poetry run python src/database/init_db.py
	@echo "📡 [3/4] Starting Backend Services (API & Worker)..."
	@# Run API and Worker in background, redirecting output to logs
	@nohup PYTHONPATH=. poetry run python src/api/main.py > backend.log 2>&1 & echo $$! > .api.pid
	@nohup PYTHONPATH=. poetry run celery -A src.worker.celery_app worker --loglevel=info > worker.log 2>&1 & echo $$! > .worker.pid
	@echo "💻 [4/4] Starting Frontend..."
	@cd frontend && npm run dev

stop:
	@echo "🛑 Stopping Frontend, API, and Worker..."
	@# Kill processes by PID file if they exist
	@[ -f .api.pid ] && kill $$(cat .api.pid) && rm .api.pid || true
	@[ -f .worker.pid ] && kill $$(cat .worker.pid) && rm .worker.pid || true
	@# Fallback pkill for Vite (Frontend)
	@pkill -f "vite" || true
	@echo "🐳 Stopping Docker containers..."
	docker compose down
	@echo "✅ All services stopped."

init:
	poetry run python src/database/init_db.py

api:
	poetry run python src/api/main.py

worker:
	poetry run celery -A src.worker.celery_app worker --loglevel=info

frontend:
	cd frontend && npm run dev
