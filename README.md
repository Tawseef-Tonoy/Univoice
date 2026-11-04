# Univoice

Univoice is a university issue-sharing application. Students can create accounts,
post issues, discuss them through comments, and upvote posts. FastAPI serves the
JSON API and Jinja HTML pages; MySQL stores users and their activity.

## Verified features

- Account registration and password login with a signed session cookie.
- An authenticated home page and post creation, listing, and detail retrieval.
- Comments and one upvote per user/post, with upvote toggling and activity counts.
- User profiles containing their posts and comments.
- Database persistence across removal and recreation of the app and DB containers.

## Architecture

The browser calls FastAPI/Uvicorn on port 8000. Routes in `routes/` validate requests
using `schemas/` and call SQLAlchemy queries in `database.py`. The app connects to
MySQL through PyMySQL. `templates/` contains Jinja pages and browser JavaScript;
`static/` contains local styles. Passwords are hashed with bcrypt and session
cookies are signed with itsdangerous.

Compose runs two services: `app` and `db`. Only the app's port is published, on
host loopback. MySQL data lives in the named `mysql_data` volume.

## Prerequisites

- Git, Docker Engine or Docker Desktop, and Docker Compose v2 or later with `--wait`.
- A running Docker daemon and network access for the first image/dependency download.
- An available local port 8000, or a different `APP_PORT`.
- Python 3 on the host for the standard-library smoke test; host Python is not
  required to run the app. OpenSSL can generate configuration secrets.

## Get the code

```bash
git clone https://github.com/Tawseef-Tonoy/Univoice.git
cd Univoice
```

If validating this update before merge, check out `feat/docker-compose-mysql`.

## Run with Docker

Install Docker Engine or Docker Desktop with Docker Compose, and start the Docker daemon.
From the repository directory, check the daemon. For Docker Desktop on Linux, select its
context explicitly (omit `--context desktop-linux` when using Docker Engine):

```bash
docker --context desktop-linux info
```

The commands below use the Docker Desktop context:

```bash
cp .env.docker.example .env.docker
# Edit .env.docker: replace both database passwords and SECRET_KEY.
# Generate each value separately with: openssl rand -hex 32
docker --context desktop-linux compose --env-file .env.docker up --build -d --wait
```

Open http://localhost:8000 to register and log in. API docs are at
http://localhost:8000/docs. Set `APP_PORT` in `.env.docker` to change the host port.
Always use `--env-file .env.docker` with the commands below. Your existing `.env`
for running Python directly is left intact; Compose explicitly supplies its own
configuration to the app. Neither environment file is copied into the image.

## Configuration

Copy the example once and edit `.env.docker`; do not overwrite an existing file
with working credentials. Use different random values for both passwords and the
session key. Generated hexadecimal values avoid shell/Compose interpolation
surprises; quote literal values containing `$` in the env file with single quotes.

| Variable | Purpose | Default / requirement |
| --- | --- | --- |
| `MYSQL_DATABASE` | Initial database and app database name | `univoice` |
| `MYSQL_USER` | Dedicated application DB user | `univoice` |
| `MYSQL_PASSWORD` | Application DB password | Required |
| `MYSQL_ROOT_PASSWORD` | MySQL administration password | Required; app does not receive it |
| `SECRET_KEY` | Signs login sessions | Required; keep stable |
| `APP_PORT` | Host HTTP port, bound to `127.0.0.1` | `8000` |
| `SESSION_COOKIE_SECURE` | Send session cookie only over HTTPS | `false` in Compose; `true` outside Compose |

Compose maps the database values into `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`,
and `DB_PASSWORD` for the app. `DB_HOST=db` uses Compose service discovery.
The original `DATABASE_URL` fallback remains in code for non-Compose use; the
verification below covers Compose. Environment files are ignored by Git and Docker.

## How the setup works

- `Dockerfile` uses Python 3.12 and the existing pinned requirements. A build stage
  compiles wheels (including the existing mysqlclient dependency); the final stage
  keeps the runtime library and installs those wheels. The app runs as a non-root
  user, with templates and static assets included, using Uvicorn on port 8000.
- `compose.yaml` runs `app` and MySQL 8.4 (`db`) on a private Compose network.
  The app reaches MySQL at `db:3306`, not `localhost`. MySQL has no published host
  port. The web port binds to host loopback for local use.
- MySQL creates a dedicated database and application user. The app uses this user,
  not root. Separate connection fields avoid URL escaping problems with passwords.
  Running Python directly still supports the original `DATABASE_URL` setting.
- MySQL's health check authenticates as the app user and queries `users`; Compose
  waits for it before starting the app. `/health` checks database access, and the
  app container health check calls it. Restart policies recover exited containers;
  an unhealthy status alone does not trigger a restart.
- The named `mysql_data` volume stores `/var/lib/mysql` outside the container.
  Rebuilding the app or running `down` keeps the data. Keep the same Compose project
  name/directory to reuse the same volume.
- No schema, migrations, or ORM definitions were found in the original repository.
  `docker/mysql/001-schema.sql` was reconstructed from `database.py`: users, posts,
  comments, and upvotes, with UUID string IDs, timestamps, foreign keys, cascading
  deletion, and one vote per user/post. The three existing post statuses are retained.
  It creates no sample users or admin accounts.
- MySQL runs the initialization SQL **only on an empty data directory**. Editing
  that file or changing database credentials in the env file does not update an
  existing volume. Apply reviewed migrations or SQL explicitly to existing databases.
  If you have an external schema or dump, compare it before importing; this inferred
  schema is a fresh-install baseline, not a migration for an existing database.
- `SESSION_COOKIE_SECURE=false` permits login on local HTTP. Set it to `true` when
  deploying behind HTTPS. Outside Compose, its default remains `true`. Keep
  `SECRET_KEY` stable across restarts so existing sessions continue to work.

## Verify and maintain

```bash
# Check configuration without printing secrets
docker --context desktop-linux compose --env-file .env.docker config --quiet
docker --context desktop-linux compose --env-file .env.docker ps
docker --context desktop-linux compose --env-file .env.docker logs --tail=100 app db

# Requires only Python 3's standard library on the host
python3 scripts/smoke_test.py
# For a different port: BASE_URL=http://localhost:8080 python3 scripts/smoke_test.py

# Rebuild after code changes (source is baked into the image)
docker --context desktop-linux compose --env-file .env.docker up --build -d --wait

# Stop/remove containers and network; retain database
docker --context desktop-linux compose --env-file .env.docker down
```

The smoke test checks registration, session login and home rendering, post creation
and retrieval, comments, upvote toggling and counts, and profile retrieval. It leaves
a unique test user/post behind for inspection. To verify persistence automatically:

```bash
# Use a new state filename each time; it holds a disposable user's password.
python3 scripts/smoke_test.py --save-state /tmp/univoice-smoke-state.json
docker --context desktop-linux compose --env-file .env.docker down
docker --context desktop-linux compose --env-file .env.docker up -d --wait
python3 scripts/smoke_test.py --verify-state /tmp/univoice-smoke-state.json
```

The second test logs in as the same user and checks the original post, comment,
upvote, counts, and profile without creating replacement records. The state file
is created with owner-only permissions. Delete it when finished.

To open a database console without exposing MySQL on the host:

```bash
docker --context desktop-linux compose --env-file .env.docker exec db sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE"'
```

Back up before schema or MySQL upgrades. A logical backup can be made with:

```bash
docker --context desktop-linux compose --env-file .env.docker exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --no-tablespaces --set-gtid-purged=OFF "$MYSQL_DATABASE"' > backup.sql
```

Keep backups private and outside version control. Restore into an appropriate,
reviewed database using `mysql` through `exec -T`; verify the backup before relying
on it. `docker --context desktop-linux compose --env-file .env.docker down -v` **permanently deletes the
local database volume**; use only when intentionally resetting disposable data.

## Troubleshooting

| Symptom | Check / action |
| --- | --- |
| Cannot connect to Docker | Start Docker Desktop/Engine and run `docker --context desktop-linux info`. Use `docker context ls` to find the appropriate context. |
| Host port already allocated | Change `APP_PORT` in `.env.docker`, rerun `up -d --wait`, and set `BASE_URL` for the smoke test. |
| DB unhealthy or app cannot connect | Inspect `compose logs --tail=100 db app` using the same context and env file as setup. Check that credentials match those used to initialize the volume. |
| Schema or password edits have no effect | Init SQL and MySQL user creation run only for an empty volume. Existing data needs an explicit reviewed migration or credential update. |
| Login succeeds but home returns to login | For local HTTP, use `SESSION_COOKIE_SECURE=false`; after configuration changes recreate the app with `up -d --wait`. |
| Smoke-test state file already exists | Use a new filename with `--save-state`; `--verify-state` reads the existing file. |
| Styles or icons fail offline | Templates use external Bootstrap/Google Fonts resources; browser presentation may require internet access. |

## Limitations

This is a local development setup. The existing API accepts usernames in mutation
requests and permits a role in registration; it does not enforce ownership through
session authentication. Anonymous presentation is handled in the frontend and does
not hide usernames in API responses. These behaviors are preserved, so public
hosting needs an authentication/authorization review, HTTPS, and managed secrets.
The schema is an inferred fresh-install baseline, with no migration framework.
There is no automated browser JavaScript coverage. Backup/restore commands are
maintenance guidance, not a verified restore workflow.

## Verification status for this change

Verified on 2026-11-04 using `docker --context desktop-linux` (Engine 29.8.2):

- Image build and fresh MySQL 8.4.13 schema initialization passed.
- Both Compose services reached healthy status; the app is published at
  `http://localhost:8000`, with MySQL accessible only inside the Compose network.
- Smoke test passed registration, cookie login and authenticated home rendering,
  post creation/list/detail, comments, upvote add/remove/add and counts, and profiles.
- Persistence passed after `compose down` and `compose up -d --wait`: both container
  IDs changed, the `univoice_mysql_data` volume remained, and the saved user's login,
  original post, comment, upvote, counts, and profile were verified without reseeding.
- The runtime runs as non-root and contains no `.env` files or cached bytecode
  under `/app`. Tracked bytecode and OS metadata were removed from Git.
- Compose configuration validation, Python syntax checks, and `git diff --check`
  passed. No remaining runtime blockers were observed for these checks.

The containers and disposable smoke-test records are retained for inspection.
Verification used the actual HTTP API; it did not automate browser JavaScript.
