.PHONY: install
install:
	pip install -U pip
	pip install -r requirements.txt

.PHONY: isort
isort:
	isort -rc -w 120 app
	isort -rc -w 120 tests

.PHONY: lint
lint:
	flake8 app/ tests/

.PHONY: reset-db
reset-db:
	python -c "from app.management import prepare_database; prepare_database(True)"

.PHONY: search-index
search-index:
	python -c "from app.management import update_index; update_index()"
