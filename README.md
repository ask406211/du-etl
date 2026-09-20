# Ducks Unlimited University Chapters — ETL Pipeline

Extracts university chapters from the Ducks Unlimited ArcGIS Feature Service,
filters them to California, and loads them into Postgres. Packaged as a
container and deployed to Google Cloud as a scheduled batch job.

---

## Architecture

```
GitHub push (main)
      |
      v
GitHub Actions ---- Workload Identity Federation (no stored keys) ----> GCP
      |  1. ruff / mypy / pytest
      |  2. docker build
      |  3. push image  ------------------------> Artifact Registry (private)
      |  4. terraform apply ---------------------> everything below
      v
Cloud Scheduler --- daily 06:00 UTC, OAuth ---> Cloud Run Job
                                                     |
                                  DATABASE_URL from Secret Manager
                                                     |
                                  unix socket /cloudsql/<instance>
                                                     v
                                          Cloud SQL for PostgreSQL
```

| Layer | Module | Responsibility |
|---|---|---|
| Extract | `src/du_etl/extract.py` | ArcGIS query, retries, pagination |
| Transform | `src/du_etl/transform.py` | Validate, map fields, filter by state |
| Load | `src/du_etl/load.py` | Idempotent upsert |
| Config | `src/du_etl/config.py` | All environment access, in one place |
| Orchestration | `src/du_etl/main.py` | Wire the three together, set exit code |

`transform.py` imports neither `httpx` nor `psycopg`. The logic with the
interesting edge cases in it is testable without a network or a database.

---

## Run it locally

Requires Docker only.

```bash
git clone <this repo> && cd du-chapters-etl
docker compose run --rm --build etl
```

Expected output:

```json
{"severity": "INFO", "message": "pipeline starting for states=['CA']", "logger": "du_etl"}
{"severity": "INFO", "message": "transform complete: received=3 kept=3 skipped=0 states=['CA']", "logger": "du_etl.transform"}
{"severity": "INFO", "message": "upserted 3 chapters", "logger": "du_etl.load"}
{"severity": "INFO", "message": "pipeline succeeded fetched=3 loaded=3 duration_s=0.85", "logger": "du_etl"}
```

Inspect the result:

```bash
docker compose exec postgres psql -U du -d du \
  -c "SELECT chapter_id, chapter_name, city, state, latitude, longitude FROM university_chapters ORDER BY chapter_id;"
```

```
 chapter_id |              chapter_name               |      city       | state | latitude  |  longitude
------------+-----------------------------------------+-----------------+-------+-----------+-------------
 CA-0300    | Chico State University                  | Chico           | CA    | 39.739982 | -121.835463
 CA-0355    | California Polytechnic State University | San Luis Obispo | CA    | 35.274309 | -120.663191
 CA-0362    | Fresno State                            | Fresno          | CA    | 36.823545 | -119.739595
```

Run it twice — the row count stays at 3. The load is idempotent.

Tear down with `docker compose down -v`.

> Postgres is published on host port **55432**, not 5432, because 5432 is
> frequently occupied by a locally installed Postgres. Override with
> `POSTGRES_HOST_PORT`.

### Without Docker

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d postgres
python -m du_etl.main
```

---

## Configuration

All configuration comes from environment variables, read in exactly one
place (`config.py`). See `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `DU_FEATURE_SERVICE_URL` | — | ArcGIS query endpoint |
| `DATABASE_URL` | — | Postgres connection string |
| `TARGET_STATES` | `CA` | Comma-separated, e.g. `CA,OR,WA` |
| `HTTP_TIMEOUT` | `30` | Seconds |
| `LOG_LEVEL` | `INFO` | |

The brief's introduction mentions CA, OR and WA while task 1 asks for CA
only. `TARGET_STATES` defaults to `CA` and satisfies both without a code
change. For reference, the API currently holds 3 CA chapters, 1 OR and 0 WA.

---

## Testing

```bash
pytest                  # 15 unit tests, no network or database
ruff check src tests
mypy src

docker compose up -d postgres
TEST_DATABASE_URL=postgresql://du:du_local_only@localhost:55432/du pytest -m integration
```

Unit tests run against a **real captured API response**
(`tests/fixtures/du_ca_response.json`) rather than a hand-written mock, so
they cannot quietly encode the same wrong assumptions as the code.

Cases worth noting:

- `test_latitude_and_longitude_are_not_swapped` — ArcGIS returns `geometry.x`
  as longitude and `geometry.y` as latitude. Swapping them puts California in
  the Indian Ocean, so the test asserts a plausible bounding box.
- `test_server_errors_are_retried` — asserts the *number of HTTP attempts*.
  A retry policy that silently never fires looks identical to a working one
  until it matters.
- `test_running_twice_does_not_duplicate` — a daily schedule guarantees
  re-processing, so idempotency is a requirement rather than a nicety.

---

## Deploy to GCP

```bash
gcloud auth login && gcloud auth application-default login
gcloud config set project YOUR-PROJECT-ID

cd infra
cp terraform.tfvars.example terraform.tfvars   # set project_id, github_repository
terraform init
terraform apply
```

The image must exist before the first apply, because Cloud Run validates it
at deploy time. Bootstrap once:

```bash
terraform apply -target=google_artifact_registry_repository.etl
gcloud auth configure-docker us-central1-docker.pkg.dev
docker build -t us-central1-docker.pkg.dev/PROJECT/du-etl/du-etl:bootstrap .
docker push    us-central1-docker.pkg.dev/PROJECT/du-etl/du-etl:bootstrap
terraform apply -var="image=us-central1-docker.pkg.dev/PROJECT/du-etl/du-etl:bootstrap"
```

After that, CI handles deployments. To trigger a run without waiting for the
schedule:

```bash
gcloud run jobs execute du-etl --region us-central1
```

### CI/CD setup

`terraform output` supplies the values. Set these as GitHub Actions
**repository variables** — no secrets are needed, which is the point of
Workload Identity Federation:

`GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_CICD_SERVICE_ACCOUNT`

---

## Design decisions

**Cloud Run Job, not a Service.** The pipeline runs to completion and exits.
A Service must listen on a port and stay resident, which is the wrong shape
for batch work and bills for idle time.

**Upsert on `chapter_id`.** Anything on a schedule eventually runs twice — a
retry, a manual trigger, a duplicated cron fire. `ON CONFLICT DO UPDATE`
makes that harmless. `chapter_id` (`CA-0355`) is the key rather than ArcGIS's
`OBJECTID`, which is an internal row counter that can be reassigned when the
layer is republished.

**`first_seen_at` is never updated.** One extra column buys a record of when
each chapter first appeared.

**Coordinates as two numeric columns.** PostGIS would be overkill for point
data only ever read back as a pair.

**One connection string, not five variables.** A single value to rotate, and
the same code path serves local TCP and the Cloud SQL unix socket
(`?host=/cloudsql/...`), so no environment branching in application code.

**Cloud SQL with an empty allow-list.** The instance has a public endpoint
because the Cloud SQL Auth Proxy requires one, but `authorized_networks` is
empty and `ssl_mode` is `ENCRYPTED_ONLY`, so every connection must be
IAM-authenticated through the proxy — a password alone reaches nothing.
Cloud Run mounts it as a unix socket, which avoids a paid VPC connector.
Private IP would remove the public endpoint altogether, at the cost of a VPC
and service-networking peering.

**Workload Identity Federation over a service account key.** A JSON key is a
long-lived credential sitting in a GitHub secret. WIF issues a short-lived
token and is pinned to this one repository via `attribute_condition`.

**Deploy the commit SHA, not `latest`.** It stays unambiguous what is
running, and a rollback is just a previous tag.

**Malformed records are skipped, not fatal.** One bad row out of 147 should
not sink the run — but it is counted and logged with a traceback rather than
silently dropped.

---

## Cost

Cloud Run Jobs, Cloud Scheduler, Artifact Registry and Secret Manager are
effectively free at this volume. **Cloud SQL is the only resource that costs
money at rest**, roughly $8–10/month for `db-f1-micro`.

Mitigations: set a budget alert before deploying; backups are disabled and
storage is `PD_HDD` for this exercise; untagged images expire after 7 days;
and `create_database = false` points the job at an existing database instead.

```bash
terraform destroy   # removes everything, including the database
```

---

## Known limitations

**Terraform state is local, so the `deploy` workflow cannot apply
infrastructure yet.** State lives in `infra/terraform.tfstate`, which is
gitignored because it stores the generated database password in plaintext.
GitHub Actions therefore starts with empty state, concludes that nothing
exists, and fails trying to recreate resources that are already deployed.

The `ci` workflow (lint, types, unit and integration tests, `terraform
validate`) is unaffected and passes.

Everything in this repository *was* deployed and verified — the
infrastructure was applied from a workstation, the Cloud Run Job executed
successfully against Cloud SQL, and the daily schedule is live. Only the
automated path for infrastructure changes is incomplete.

The fix is item 1 below and takes roughly ten minutes. It was left out
deliberately as a time trade-off rather than overlooked.

---

## What I would do next

Ordered by what I would pick up first.

1. **Remote Terraform state.** A versioned GCS bucket with object
   versioning and restricted IAM; the backend block is present and
   commented in `versions.tf`. This closes the limitation above and is a
   prerequisite for more than one person touching the infrastructure.
2. **Alembic migrations.** The schema is applied with
   `CREATE TABLE IF NOT EXISTS` on each run, which handles creation but not
   evolution. Alembic gives versioned, reversible changes.
3. **Alerting.** A log-based metric on non-zero job exits wired to a
   notification channel. Today a failure is visible only in Cloud Logging.
4. **`terraform plan` on pull requests**, posted as a PR comment, so
   infrastructure changes are reviewed before merge.
5. **Historical tracking.** The table holds current state only. A
   slowly-changing-dimension table would preserve chapter history.
6. **Image scanning** and a dependency lockfile for reproducible builds.
7. **Separate bootstrap stack.** Registry and WIF logically precede the
   application stack; splitting them removes the manual first-push step.
