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

.PHONY: test
test:
	py.test --cov=app --isort

.PHONY: test-buildcov
test-buildcov:
	py.test --cov=app && (echo "building coverage html, view at './htmlcov/index.html'"; coverage html)

.PHONY: reset-db
reset-db:
	python -c "from app.management import prepare_database; prepare_database(True)"

.PHONY: db-populate
db-populate:
	python -c "from app.management import populate_dummy_db; populate_dummy_db()"
