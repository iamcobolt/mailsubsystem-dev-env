SHELL := /bin/bash

ENV_FILE ?= .env
COMPOSE := docker compose --env-file $(ENV_FILE) -f docker-compose.yml

.PHONY: init certs start stop reset logs ps import core-env check-core

init: ## Create .env and local trusted IMAP TLS certificates
	@if [ ! -f $(ENV_FILE) ]; then cp .env.example $(ENV_FILE); echo "Created $(ENV_FILE) from .env.example"; fi
	./scripts/setup-trusted-certs.sh

certs: ## Create or refresh local trusted IMAP TLS certificates
	./scripts/setup-trusted-certs.sh

start: init check-core ## Start PostgreSQL + Dovecot sandbox
	$(COMPOSE) --profile sandbox up -d --wait
	@DB_PORT="$$(grep -E '^MAILSUBSYSTEM_DB_PORT=' $(ENV_FILE) | cut -d= -f2-)"; \
	IMAPS_PORT="$$(grep -E '^SANDBOX_IMAPS_PORT=' $(ENV_FILE) | cut -d= -f2-)"; \
	IMAP_PORT="$$(grep -E '^SANDBOX_IMAP_PORT=' $(ENV_FILE) | cut -d= -f2-)"; \
	echo ""; \
	echo "MailSubsystem development environment is running."; \
	echo "  IMAPS: localhost:$${IMAPS_PORT:-1993}"; \
	echo "  IMAP:  localhost:$${IMAP_PORT:-1143}"; \
	echo "  DB:    localhost:$${DB_PORT:-15432}"; \
	echo ""; \
	echo "To create a sandbox .env in the core repo:"; \
	echo "  make core-env"

stop: init ## Stop services, preserving Docker volumes
	$(COMPOSE) --profile sandbox down

reset: init check-core ## Stop services, wipe Docker volumes, and start fresh
	$(COMPOSE) --profile sandbox down -v
	$(COMPOSE) --profile sandbox up -d --wait

logs: init ## Follow service logs
	$(COMPOSE) --profile sandbox logs -f

ps: init ## Show service status
	$(COMPOSE) --profile sandbox ps

import: ## Import .eml files or mbox into the sandbox (set EMAILS=/path)
	@test -n "$(EMAILS)" || (echo "Set EMAILS=/path/to/emails-or-mailbox" >&2; exit 1)
	python3 scripts/import-emails.py "$(EMAILS)"

core-env: init ## Write a sandbox .env into the MailSubsystem core checkout
	./scripts/write-core-env.sh

check-core: init ## Verify the configured MailSubsystem checkout exists
	@CORE_DIR="$$(grep -E '^MAILSUBSYSTEM_CORE_DIR=' $(ENV_FILE) | cut -d= -f2-)"; \
	CORE_DIR="$${CORE_DIR:-../MailSubsystem}"; \
	test -f "$$CORE_DIR/schema.sql" || \
		(echo "MailSubsystem core schema not found at $$CORE_DIR/schema.sql"; \
		 echo "Edit $(ENV_FILE) and set MAILSUBSYSTEM_CORE_DIR to your core checkout."; exit 1)
