# Space Fractions — Architecture Documentation

## A. Executive Summary

Space Fractions is an interactive fraction-learning tool for sixth-grade
students. It presents an introductory scene, a main menu, a series of fraction
questions, and an ending scene with feedback. The original web/microservices
architecture is preserved (Game, Question, User, Admin components); a later
delivery constraint (see ASSUMPTIONS.md) additionally requires a **native
Windows desktop UI** built with Python 3.12 + tkinter. The desktop UI drives the
same service boundaries so both the web/API path and the desktop path remain
consistent.

- Architectural style: microservices (service boundaries in `spacefractions/services.py`)
- Deployment topology: cloud (Kubernetes) for the API path; PyInstaller-packaged
  `.exe` for the desktop path
- UI framework: tkinter (native desktop)

Top 3 design risks and mitigations:

| Risk | Mitigation |
| --- | --- |
| Scalability | k8s replicas=3, load balancing, autoscaling-ready probes |
| Security | OAuth2-style authn, role-based admin authz, TLS/service-mesh plan |
| Data loss | PostgreSQL persistence + replication and backup plan |

## B. Traceability & Rationale

Full mapping (all catalog IDs, including derived SF-* and EMAIL-DESKTOP) is in
`traceability_matrix.csv` and `implementation-map.json`.

## C. Architecture Overview

Components (SF-SERVICES):

- **GameService** (`spacefractions/services.py`) — game logic, session state machine.
- **QuestionService** — question management and persistence delegation.
- **UserService** — player authentication and identity.
- **AdminService** — authorized question editing.

Each service maps to a PlantUML component (GameComponent, QuestionComponent,
UserComponent, AdminComponent). The written overview in the source document
omitted Admin; this architecture reconciles Admin as a first-class service
(see ASSUMPTIONS.md).

## D. Detailed Technical Design

### GameService
- Responsibility: session orchestration, state transitions (Playing/Paused/GameOver), scoring.
- Data ownership: in-flight game state (persisted via `GameRepository`).

### QuestionService
- Responsibility: CRUD for questions; owns question data.
- Persistence: `QuestionRepository` with PostgreSQL (`PostgresQuestionRepository`)
  and a documented SQLite offline adapter (`SQLiteQuestionRepository`).

### UserService / AdminService
- UserService: authentication (demo credential store; production OAuth2).
- AdminService: authorization gate around question mutations (role == "admin").

### Technology options (3+ alternatives per component)

| Component | Alternatives | Chosen | Rationale |
| --- | --- | --- | --- |
| Language/runtime | Node.js, Java, Python | Python 3.12 | Desktop UI + API parity, per email |
| UI | Web (Flask/React), webview, native | tkinter/ttk | EMAIL-DESKTOP native requirement |
| Persistence | PostgreSQL, MySQL, SQLite | PostgreSQL (+SQLite offline) | SF-PERSIST, ASR-1 durability |
| Cache | Redis, Memcached, in-memory | Redis (deferred for desktop) | NFR-1 |
| Messaging | RabbitMQ, Kafka, in-proc | RabbitMQ (deferred) | ASR-2 |
| Authn/authz | OAuth2, JWT, basic | OAuth2 + role check | ASR-2, SF-SECURITY |
| Observability | Prometheus, Datadog, logging | Prometheus | NFR-1, SF-OPS |
| Container | Docker, Podman, bare metal | Docker | SF-DEPLOY |

### Interface design

External API: `openapi.yaml` (play, questions, score). Internal RPC:
`internal.proto` (GameService, QuestionService, AdminService).

### Data model / schema

- `sql/game_ddl.sql` — `games(id, game_state JSONB)`.
- `sql/question_ddl.sql` — `questions(id, prompt, options TEXT[], correct_answer)`.

### Caching & consistency

Redis caches game state in the API path (deferred for desktop); PostgreSQL is
the system of record; read-after-write on answers is direct.

## E. Operations & Deployment

- `k8s/spacefractions-deployment.yaml` — 3 replicas, probes, limits.
- DB HA: PostgreSQL replication; backups documented in runbook (SF-OPS).
- Desktop packaging: `build_game.ps1` → `Space-Fractions.exe` (PyInstaller `--onefile --windowed`).
- Containers: `Dockerfile` + `docker-compose.yml` (Postgres + service) for demo.

## F. Security Design

- AuthN: OAuth2 (service path); demo credentials for desktop/admin login.
- AuthZ: `Admin.is_authorized()` gates question updates; negative tests in
  `tests/test_services.py` and `tests/test_controller.py`.
- Secrets: Vault (documented); rotation policy in runbook.
- TLS: mTLS + service mesh (Istio) for the API path.
- Threat model: unauthorized access, data breach, DoS, malware, phishing.

## G. Observability & SRE

Per-component metrics: game start/completion rate, question response/accuracy.
SLOs/error budgets/RTO/RPO are documented in ASSUMPTIONS.md (the 99.99%/1%
conflict is resolved there). Dashboards and runbooks are described in
`docs/runbook.md`.

## H. Testing Strategy

| Type | GameService | QuestionService | AdminService | Desktop |
| --- | --- | --- | --- | --- |
| Unit | yes | yes | yes | yes (controller) |
| Integration | yes | yes | yes | — |
| Contract | openapi/proto | openapi/proto | proto | — |
| E2E | manual | manual | manual | manual |
| Chaos | deferred | deferred | deferred | — |

Test data: `spacefractions/sample_questions.py`; environments isolated via
Docker/Kubernetes (documented).

## I. Migration, Data Conversion & Rollout Plan

See SF-ROLLOUT in `traceability_matrix.csv`. High-level: migrate game/question
tables, dual-write during transition, 1-month migration window, 1-year backward
compatibility for public APIs.

## J. Tradeoffs & Alternatives

Monolith vs microservices vs serverless; chosen microservices-bounded-in-process
for the desktop demo while keeping deployable service boundaries.

## K. Open Questions & Assumptions

See ASSUMPTIONS.md (A1/A2 user counts, error-budget conflict, admin coverage,
desktop reconciliation, deferred infrastructure).

## L. Deliverables

architecture.md, openapi.yaml, internal.proto, k8s/spacefractions-deployment.yaml,
sql/game_ddl.sql, sql/question_ddl.sql, desktop.py, desktop-manifest.json,
build_game.ps1, traceability_matrix.csv, implementation-map.json,
requirements.txt, Dockerfile, docker-compose.yml, tests/.
