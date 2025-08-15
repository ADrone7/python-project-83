install:
	uv sync

lint:
	uv run ruff check

build:
	chmod +x build.sh && ./build.sh

dev:
	uv run flask --debug --app page_analyzer:app run

PORT ?= 8000
start:
	uv run gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app --timeout 90

render-start:
	gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app --timeout 90