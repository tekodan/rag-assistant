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
