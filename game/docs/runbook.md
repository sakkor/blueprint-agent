# Space Fractions — Operations Runbook (SF-OPS)

## Health checks

- API path: `GET /healthz` (see `spacefractions/health.py`).
- k8s probes configured in `k8s/spacefractions-deployment.yaml`.

## Database initialization

```bash
docker compose up db          # runs sql/*.sql on first start
# or manually:
psql -f sql/game_ddl.sql
psql -f sql/question_ddl.sql
```

Seed questions are provided in `spacefractions/sample_questions.py` and are
auto-seeded on first run by `ui.seed_services`.

## Backup & recovery (plan, not certified)

- Nightly `pg_dump` of `spacefractions` DB.
- WAL archiving + point-in-time recovery (PITR) to a separate region.
- RTO/RPO target: 1 hour (see ASSUMPTIONS.md; not validated).

## Observability

- Prometheus metrics (deferred): game start/completion rate, per-question accuracy.
- Dashboards: Grafana (documented); runbook covers high-error and high-latency pages.

## Secret rotation

- Vault (documented): rotate DB/API secrets every 90 days; full rotation window 7 days.

## Verification plan for quality requirements

| ID | Metric | Verification |
| --- | --- | --- |
| ASR-1 | RPO/RTO | DR drill, backup restore test, replication lag monitor |
| ASR-2 | ATO | Pen test, vuln scan, authz negative tests (already in tests/) |
| NFR-1 | P99 latency | Load test with k6/Locust; autoscaling threshold tuning |
| SF-OPS | SLO 99.99% | Burn-rate alerting with 0.01% error budget |

These are verification plans; none have been executed by this harness.
