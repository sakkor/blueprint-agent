# Space Fractions - locally checked demo

A native Windows desktop fraction-learning demo implemented in Python 3.12 and Tkinter. This is the locally repaired output of a DeepSeek generation run.

The desktop UI uses in-memory state. Scores and question changes reset when the application closes. PostgreSQL and SQLite adapters are included, but PostgreSQL integration is unverified and neither adapter is wired into the default UI. See LOCAL-REVIEW.md.

This source repository excludes the executable. Run desktop.py using the instructions below, or build the executable with build_game.ps1. Running the game does not call DeepSeek.

## Desktop launch (native UI)

```bash
# Install (Windows / Python 3.12)
pip install -r requirements-dev.txt

# Run the desktop game
python desktop.py
```

This opens a real `tkinter.Tk` window with a `mainloop`, providing intro, main
menu, help, play/pause/resume, score, game-over feedback, and an admin
question-editing screen. No browser or webview is used.

### Admin (demo credentials — NOT secure)

- Username `admin`, password `admin` (question editing)
- Player `player` / `play`

## Packaging (build the .exe)

```
powershell -File build_game.ps1
```

`build_game.ps1` runs the test suite (`python -m pytest -q`) and then packages
the game with PyInstaller:

```
python -m PyInstaller --onefile --windowed --name Space-Fractions desktop.py
```

Output: `dist/Space-Fractions.exe`.

## Tests

```bash
python -m pytest -q
```

Tests cover the domain model, service boundaries, the headless desktop
controller/state behavior (pause/resume/score), persistence (SQLite offline
adapter), and negative admin authorization cases. The 25 local tests passed after the repairs documented in LOCAL-REVIEW.md.

## PostgreSQL adapter (integration unverified)

The intended PostgreSQL persistence adapter is (`spacefractions/storage.py`,
`PostgresQuestionRepository` / `PostgresGameRepository`) with schemas:

- `sql/game_ddl.sql`
- `sql/question_ddl.sql`

Initialize via Docker:

```bash
docker compose up db   # auto-runs sql/*.sql
```

## Optional SQLite offline adapter (demo only)

`SQLiteQuestionRepository` (`spacefractions/storage.py`) enables a quick local
demo without PostgreSQL. It does **not** satisfy PostgreSQL deployment, HA, or
production requirements (see `ASSUMPTIONS.md`).

## Project layout

- `desktop.py` — desktop entry point (mainloop)
- `desktop-manifest.json` — required manifest
- `build_game.ps1` — test + PyInstaller packaging
- `spacefractions/` — model, services, storage, ui, health
- `openapi.yaml`, `internal.proto` — contracts
- `k8s/`, `sql/`, `Dockerfile`, `docker-compose.yml` — deployment
- `docs/runbook.md` — ops/runbook
- `traceability_matrix.csv`, `implementation-map.json` — traceability

See `architecture.md`, `ASSUMPTIONS.md`, and `PLAN.md` for full design.
