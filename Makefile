# REC Guard — developer shortcuts
PY ?= backend/venv/bin/python

.PHONY: setup keys db backend frontend test test-backend test-frontend seed docker docker-prod clean

setup:            ## create venv, install backend + frontend deps, keys, db
	cd backend && python3.11 -m venv venv && venv/bin/pip install -r requirements.txt
	cp -n backend/.env.example backend/.env || true
	cp -n frontend/.env.example frontend/.env || true
	cd frontend && npm install
	$(MAKE) keys db

keys:             ## generate RSA-2048 key pair (once)
	cd backend && venv/bin/python scripts/generate_keys.py

db:               ## initialise the SQLite ledger
	cd backend && venv/bin/python scripts/init_db.py

backend:          ## run the Flask API on :5000
	cd backend && venv/bin/python app.py

frontend:         ## run the Vite dev server on :5173
	cd frontend && npm run dev

seed:             ## load the demo scenarios (valid + 4 fraud cases) into the ledger
	cd backend && venv/bin/python scripts/seed_demo.py

test: test-backend test-frontend

test-backend:
	cd backend && venv/bin/python -m pytest tests/ -q --cov=. --cov-report=term -p no:logging

test-frontend:
	cd frontend && npm test

docker:           ## dev stack on :3000 (UI) and :5000 (API)
	docker compose up --build

docker-prod:
	docker compose -f docker-compose.prod.yml up -d --build

clean:
	rm -rf backend/storage/ledger.db* backend/storage/certificates/* backend/storage/temp/* backend/htmlcov frontend/dist
