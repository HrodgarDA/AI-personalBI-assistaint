# AI Personal BI Assistant - Makefile

.PHONY: start stop restart clean

start:
	@echo "🚀 Starting services in Docker..."
	docker-compose up -d
	@echo "⏳ Waiting for database to be ready..."
	sleep 3
	@echo "🛠️ Running database migrations..."
	export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/personal_bi" && poetry run alembic upgrade head
	@echo "📈 Starting Streamlit UI..."
	poetry run streamlit run app/webapp.py

stop:
	@echo "🛑 Stopping all services..."
	docker-compose down
	@echo "👋 UI closed (press Ctrl+C in the terminal if streamlit is still running)."

restart:
	$(MAKE) stop
	$(MAKE) start

clean:
	@echo "🧹 Cleaning up docker volumes and temporary files..."
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} +
