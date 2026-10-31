# PLAN.md — Implementation Plan

## Approach

1. Implement domain model (Game, Question, User, Admin) matching the ClassDiagram.
2. Implement service boundaries (Game/Question/User/Admin services).
3. Implement storage: PostgreSQL adapter (primary) + SQLite offline adapter (demo).
4. Implement native tkinter desktop UI over a headless, testable controller.
5. Produce contracts (OpenAPI, protobuf), schemas (SQL DDL), k8s, Docker, packaging.
6. Write tests; produce traceability matrix and implementation map.

## Component responsibilities

| Component | File | Responsibility |
| --- | --- | --- |
| Model | spacefractions/model.py | Entities + state machine |
| GameService | spacefractions/services.py | Session orchestration, scoring |
| QuestionService | spacefractions/services.py | Question CRUD, persistence delegation |
| UserService | spacefractions/services.py | Authentication |
| AdminService | spacefractions/services.py | Authorized question edits |
| Storage | spacefractions/storage.py | PostgreSQL + SQLite adapters |
| UI | spacefractions/ui.py | tkinter views (thin) |
| Controller | spacefractions/ui.py | Headless state driver (testable) |
| Desktop entry | desktop.py | mainloop launch |
| Packaging | build_game.ps1 | pytest + PyInstaller .exe |

## Delivery checklist

- Native desktop window + mainloop (EMAIL-DESKTOP)
- Intro/menu/help, play/pause/resume/score/end, admin editing (SF-INTRO, SF-PLAY, SF-SCORE, SF-HELP, SF-ADMIN, SF-STATE)
- PostgreSQL persistence + schema + documented recovery (SF-PERSIST, ASR-1)
- Authorization + negative tests (SF-SECURITY, ASR-2)
- Contracts consistent with source/schemas (SF-CONTRACTS)
- Deployment/k8s/containers (SF-DEPLOY, SF-OPS)
- Full traceability (SF-TRACE, SF-STACK, SF-ROLLOUT)

## Verification

Run `python -m pytest -q` locally (the harness does not execute shell commands;
generated tests have NOT been run by this harness).
