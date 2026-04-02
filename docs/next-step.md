# Next Steps Sequence

## Actual State (2026-03-28)

### Completed

1. End-to-end local architecture is in place with API, worker, PostgreSQL, RabbitMQ, and MinIO via Docker Compose.
2. API endpoints for upload, job status, result retrieval, health, and metrics are implemented.
3. Worker consumes queue messages and stores basic audio metadata extraction results.
4. Unit tests are green:
	API: 5 passed.
	Worker: 4 passed.
5. Python dependency management is set up with Poetry for both services.

### Partially Completed

1. Observability is present at basic level (application metrics endpoints/counters), but no complete monitoring stack/dashboard evidence yet.
2. Fault handling exists at basic level (failed jobs are marked), but retry strategy and dead-letter handling are not implemented.

### Not Completed Yet

1. Worker retry policy with max attempts and dead-letter queue.
2. Idempotency safeguards for repeated delivery scenarios.
3. User entity and authentication/authorization system.
4. API startup lifecycle migration from deprecated startup hook to lifespan.
5. Prometheus + Grafana compose integration with dashboard(s).
6. End-to-end integration tests against docker-compose.
7. Scalability benchmark comparing 1 worker vs multiple workers.
8. Kubernetes manifests and scaling demonstration.

### Current Repository Notes

1. Branch: main.
2. Local uncommitted changes exist in report files under docs/report (TeX and PDF).

This sequence is ordered by impact for the final demo and report: first identity/security foundation, then reliability, then observability, then scalability evidence, then packaging and presentation.

## 1. Identity, Authentication, and Authorization

Goal: introduce ownership and access control for uploads/jobs/results.

1. Add users table and role model (for example: USER, ADMIN).
2. Add authentication endpoints:
	register, login, token refresh (JWT-based).
3. Store secure password hashes (Argon2 or bcrypt), never plain passwords.
4. Add job ownership in data model (jobs.user_id).
5. Protect API endpoints with bearer auth.
6. Enforce authorization rules:
	users can access only their own jobs/results, admins can access all.
7. Add tests for auth success/failure and ownership boundaries.

Done criteria:
- Every upload/job/result is linked to a user.
- Unauthorized access to other users' jobs is blocked.
- Authentication and authorization behavior is covered by tests.

## 2. Reliability Hardening

Goal: ensure job processing is resilient to transient failures.

1. Add retry policy in worker consumption flow.
2. Add a max retry count in message payload or headers.
3. Route exhausted jobs to a dead-letter queue.
4. Make processing idempotent (safe if a message is delivered more than once).
5. Store failure reason and retry count in database.

Done criteria:
- A temporary dependency outage does not lose jobs.
- Failed jobs become visible and traceable.
- Re-delivered messages do not duplicate final results.

## 3. API Lifecycle Update

Goal: remove deprecated FastAPI startup pattern.

1. Replace startup event hook with lifespan handler.
2. Keep existing startup checks (DB, storage bucket) in lifespan.
3. Re-run API tests and verify no behavior change.

Done criteria:
- No startup deprecation warning appears in tests.
- Existing endpoints behave exactly as before.

## 4. Observability Completion

Goal: provide measurable evidence of system behavior.

1. Add worker processing latency histogram.
2. Add job state counters (pending, processing, done, failed).
3. Add queue depth metric (or periodic queue size sampling).
4. Add Prometheus service to compose stack.
5. Add Grafana service with at least one dashboard.

Done criteria:
- Metrics are scraped by Prometheus.
- Dashboard shows throughput, latency, and failures over time.

## 5. Integration Validation

Goal: prove end-to-end functionality beyond unit tests.

1. Add one docker-compose integration test scenario:
	upload file -> wait -> check result.
2. Add one failure scenario:
	invalid/non-WAV file still completes gracefully.
3. Add one retry scenario:
	force temporary worker failure, then verify recovery.

Done criteria:
- End-to-end tests pass against local stack.
- At least one resilience scenario is validated automatically.

## 6. Scalability Experiment

Goal: demonstrate distributed processing value.

1. Run baseline with one worker and fixed upload batch.
2. Run the same batch with multiple workers (for example 3).
3. Compare throughput and processing completion time.
4. Capture charts/screenshots for report.

Done criteria:
- Evidence shows performance difference between 1 and N workers.
- Results are reproducible with clear test setup.

## 7. Kubernetes Deliverable

Goal: align with proposal deliverables.

1. Create manifests for API, worker, broker, database, storage.
2. Add config and secrets strategy (ConfigMap + Secret).
3. Add horizontal scaling setup for worker deployment.
4. Document local execution option (Kind or equivalent).

Done criteria:
- Stack can be deployed on local Kubernetes.
- Worker replicas can be scaled without code changes.

## 8. Documentation and Final Report Support

Goal: make demo and evaluation clear and repeatable.

1. Update README with exact run/test/observe commands.
2. Add troubleshooting notes for common local issues.
3. Add experiment methodology section for report:
	dataset, load shape, metrics, hardware constraints.
4. Add final architecture diagram and data flow diagram.

Done criteria:
- Another teammate can run demo from docs only.
- Report has enough technical evidence and reproducibility detail.

## Suggested Execution Order (Updated)

1. Identity/authentication/authorization
2. Reliability hardening
3. API lifecycle update
4. Observability completion
5. Integration validation
6. Scalability experiment
7. Kubernetes deliverable
8. Documentation/report finalization

## Immediate Next Action

Start with Identity, Authentication, and Authorization in this order:

1. Add users + roles schema
2. Add JWT login/register and password hashing
3. Add jobs.user_id and ownership checks in endpoints
4. Add auth/authorization test coverage

Then continue with Reliability Hardening (retry, DLQ, idempotency).
