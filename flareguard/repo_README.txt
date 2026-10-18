REPO NOTE
--------
This repo = flareguard/flareguard/ from flareguard.zip, flattened to repo root.

Added:
- index.html         static demo of the dashboard UI (wires to the real API shape)
- demo_local.sh      one-command local launch helper (API_URL + python http.server)

Kept from the zip, unchanged:
- README.md (regenerated from the package README, plus local-demo note)
- Dockerfile / Dockerfile.ui / docker-compose.yml
- Makefile / server_setup.sh / run_api.sh / evaluate.py
- src/ (config, bootstrap, api, causal, datagen, explain, features, models)
- app/dashboard.py
- tests/
- requirements*.txt
- .env.example / .gitignore (gitignore rewritten slightly)

No team name, problem statement ID, hackathon name, or live endpoint was invented.
Fill .env or set API_URL when you have the real server.
