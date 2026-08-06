.PHONY: up down logs migrate revision seed test lint e2e api-client docs docs-api docs-erd docs-uml docs-tests reset setup

setup:      ## one-time: toolchain + hooks + deps
	mise install
	pip install pre-commit && pre-commit install
	cd frontend && npm install

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api worker

migrate:
	docker compose exec api alembic upgrade head

revision:   ## make revision m="add apply_slug"
	docker compose exec api alembic revision --autogenerate -m "$(m)"

seed:
	docker compose exec api python -m app.scripts.seed

test:
	docker compose exec api pytest -q --cov=app/services --cov-fail-under=70
	cd frontend && npm run test -- --run

e2e:
	cd e2e && npx playwright test

lint:
	pre-commit run --all-files

## ---- Contract ----
api-client: ## regenerate the typed frontend client from the live API
	docker compose exec -T api python -m app.scripts.dump_openapi > docs/openapi.json
	npx openapi-typescript docs/openapi.json -o frontend/src/lib/api.d.ts
	@echo "regenerated. commit both files together."

## ---- Generated documentation (never hand-maintained) ----
docs: docs-api docs-erd docs-uml docs-tests
	@echo "all report artifacts regenerated in docs/generated/"

docs-api:   ## OpenAPI spec — replaces the hand-written API table
	mkdir -p docs/generated
	docker compose exec -T api python -m app.scripts.dump_openapi > docs/generated/openapi.json

docs-erd:   ## ERD rendered from the live database
	mkdir -p docs/generated
	docker compose exec -T api python -m app.scripts.dump_erd > docs/generated/erd.puml
	@echo "render at plantuml.com or with the PlantUML CLI"

docs-uml:   ## class diagram from the actual models and services
	mkdir -p docs/generated
	docker compose exec -T api pyreverse -o puml -p AutoHire app/models app/services -d /app/../docs/generated

docs-tests: ## test + coverage report for the IV&V appendix
	mkdir -p docs/generated
	docker compose exec api pytest --html=/app/../docs/generated/test-report.html \
		--self-contained-html --cov=app --cov-report=html:/app/../docs/generated/coverage

reset:
	docker compose down -v && docker compose up -d --build
	sleep 8 && $(MAKE) migrate && $(MAKE) seed
