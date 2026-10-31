# Assumptions & Reconciliation Notes

This file documents assumptions, reconciliation decisions, and honest
partial/deferred status. Nothing here certifies uptime, security, or
availability; those require runtime evidence.

## 1. Desktop vs. web/microservices (EMAIL-DESKTOP)

The Professor email (2026-10-22) requires a **native Windows desktop UI**, not a
browser/web interface. This is a *later* delivery constraint layered on top of
the original web/microservices architecture. Reconciliation:

- The original microservice boundaries (Game, Question, User, Admin) are
  preserved as separate service classes (`spacefractions/services.py`) with
  clear responsibilities and API/RPC contracts (`openapi.yaml`, `internal.proto`).
- The desktop UI (`spacefractions/ui.py`, `desktop.py`) is a **thin Tk view
  layer** over those same boundaries via a headless `GameController`. There is
  no browser launch, webview, or Flask-only/HTML-only substitute.
- Packaging: `build_game.ps1` runs tests then PyInstaller `--onefile --windowed`
  to produce `Space-Fractions.exe`.

## 2. 99.99% uptime vs. 1% error budget (findings)

The source document states "SLO: 99.99% uptime" and "Error budget: 1%". A
99.99% SLO implies a **0.01%** unavailability budget; 1% is inconsistent.

**Resolution assumption:** the SLO is 99.99% availability and the *error budget*
is therefore **0.01%** (52.6 minutes/year). The "1%" figure is treated as an
editorial error in the source. We do **not** certify that this SLO is met; it is
a design target requiring production telemetry.

## 3. Derived SF-* IDs (findings)

No separate complete requirements baseline was supplied. The `SF-*`,
`EMAIL-DESKTOP`, and `FR/NFR/ASR` IDs are derived checklist IDs, not original
professor-assigned IDs. They are used consistently across the traceability
matrix and implementation map.

## 4. Admin coverage (findings)

The UML includes Admin, but part of the written component overview omits it.
We include AdminService as a first-class component and cover it in tests,
contracts, and the traceability matrix.

## 5. Object/collaboration diagrams (findings)

ObjectDiagram and CollaborationDiagram use sequence-style `participant` blocks.
We preserve the originals and interpret them as interaction/communication
diagrams (the written collaboration blocks are the source of truth for
SequenceDiagram2's admin update flow).

## 6. Deferred / partial infrastructure (findings)

The recommended infrastructure is extensive. Delivered and functional:

- Python service boundaries, PostgreSQL adapter, SQLite offline adapter,
  tkinter desktop UI, packaging script, Docker/K8s/YAML/SQL/proto contracts,
  health check, tests, docs.

Deferred (documented, not claimed as delivered or verified):

- Redis cache, RabbitMQ messaging, Elasticsearch, Prometheus scraping,
  Jenkins CI, Terraform provisioning, Istio service mesh, Vault.
- Live Kafka/message-driven flows and autoscaling are design placeholders.

## 7. Availability/throughput/security/recovery claims (findings)

Static checks cannot certify these qualities. Quality requirements (ASR-1,
ASR-2, NFR-1, SF-OPS) are implemented as *designs with a measurable
verification plan*; they are marked "partial" or "design" in the implementation
map, never "achieved".

## 8. SQLite offline adapter

`SQLiteQuestionRepository` exists only to ease the local desktop demo. It does
**not** satisfy PostgreSQL deployment, HA, or production requirements. The
production persistence path is `PostgresQuestionRepository` + `sql/*_ddl.sql`.

## 9. Intro scene asset

No movie/asset was supplied. The introductory scene is a documented text/animated
panel (an explicit asset assumption), not a supplied video.

## 10. Credentials

Demo credentials (`player/play`, `admin/admin`) are for the local demo only and
are documented as insecure. Production uses OAuth2 + hashed secrets (see
Security Design). They are never claimed to be a security control.

## 11. Model/storage consistency

`games.game_state` stores the JSON of `Game.to_dict()`; `questions.options` uses
PostgreSQL `TEXT[]` (the `PostgresQuestionRepository` reads/writes Python lists
to match). The SQLite adapter stores options as JSON text.

## 12. Original delivered snippets

The original `openapi.yaml`, `internal.proto`, k8s, and SQL snippets were
incomplete examples; they are reconciled to a coherent, valid, consistent set
rather than left as-is.
