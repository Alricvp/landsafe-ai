.PHONY: install data train api ui test eval up

install:
	pip install -r requirements-dev.txt

data:
	python3 -m src.datagen.generate

train:
	python3 -m src.models.train

api:
	python3 -m src.bootstrap && python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

ui:
	pip install -q -r requirements-ui.txt && streamlit run app/dashboard.py

test:
	python3 -m pytest -q

eval:
	python3 scripts/evaluate.py

up:
	docker compose up --build -d
