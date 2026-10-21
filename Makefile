.PHONY: all qa test lint js sitio capturas imagenes limpiar

all:            ## Todo offline: QA, base SQLite, exports y sitio (build/)
	python -m inflationarg all

qa:             ## Solo la QA de datos
	python -m inflationarg qa

test: all       ## pytest con cobertura + tests de JS
	pytest --cov --cov-report=term-missing
	npm test

lint:
	ruff check .
	ruff format --check .

sitio: all      ## Validación HTML + Playwright y axe
	npm run validar-html
	npm run qa-sitio

capturas: all   ## Capturas en build/capturas (375/768/1280, claro y oscuro)
	npm run qa-sitio -- --solo-capturas

imagenes: all   ## Regenera og.png y apple-touch-icon.png
	node scripts/generar_imagenes.mjs

limpiar:
	rm -rf build .pytest_cache .ruff_cache .coverage
