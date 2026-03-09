.PHONY: up down restart build logs logs-api ps clean help

# Default target
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  up          Build and start all services (detached)"
	@echo "  down        Stop and remove containers"
	@echo "  restart     Restart all services"
	@echo "  build       Rebuild images without starting"
	@echo "  logs        Tail logs from all services"
	@echo "  logs-api    Tail logs from the API service only"
	@echo "  ps          Show running containers and their status"
	@echo "  clean       Stop containers and remove volumes (deletes all data)"
	@echo "  shell       Open a shell inside the API container"

up:
	docker compose up --build -d
	@echo ""
	@echo "✅ RAG Assistant is running!"
	@echo ""
	@echo "  🌐 Frontend:      http://localhost:8000"
	@echo "  📖 API docs:      http://localhost:8000/docs"
	@echo ""
	@echo "  Quick examples:"
	@echo ""
	@echo "  Upload a PDF:"
	@echo "    curl -X POST http://localhost:8000/documents \\"
	@echo "         -F 'file=@your-document.pdf'"
	@echo ""
	@echo "  Ask a question:"
	@echo "    curl -X POST http://localhost:8000/chat \\"
	@echo "         -H 'Content-Type: application/json' \\"
	@echo "         -d '{\"query\": \"What is this document about?\"}'"
	@echo ""
	@echo "  Note: Ollama may take a few minutes to download models on first run."
	@echo "        Run 'make logs-api' to follow startup progress."

down:
	docker compose down

restart:
	docker compose restart

build:
	docker compose build

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

ps:
	docker compose ps

clean:
	docker compose down -v

shell:
	docker compose exec api bash
