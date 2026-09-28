# School Management System

A web application for managing students, attendance, grades, class
scheduling, parent communication, and school-wide announcements.

## Features

- Role-based accounts (admin, teacher, student, parent)
- Secure authentication: password complexity rules, account lockout after
  repeated failed logins, and HTTPS enforcement in production
- Encrypted storage for sensitive fields (SSNs, home addresses, medical
  notes, message contents) with transparent encrypt/decrypt on read and
  write
- Student enrollment and profile management
- Attendance tracking, restricted to teachers and admins
- Grade entry and report card generation, with CSV export
- Class scheduling with conflict detection (a teacher, student, or room
  can't be double-booked)
- A parent portal for viewing a child's grades and attendance, scoped so a
  parent can only ever see their own children's records
- Secure messaging between teachers and parents
- School-wide announcements
- Admin-only critical notifications
- Audit logging on every access to a student's records, granted or denied

## Tech stack

- Python
- PostgreSQL in production, SQLite for local development
- Gunicorn as the application server
- WhiteNoise for serving static files

## Project structure

```
config/            settings, URL routing, app entry points
accounts/          user accounts, login, roles/permissions, encryption, lockout
academics/         students, attendance, grades, scheduling, report cards
family_portal/     parent record access, parent<->teacher messaging
notices/           announcements, critical notifications
templates/         shared base templates
static/css/        stylesheet
```

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations accounts academics family_portal notices
python manage.py migrate
python manage.py seed_demo_data   # creates demo users + sample records
python manage.py runserver
```

Demo accounts (password `C0rrectHorse!Battery`): `demo_admin`, `demo_teacher`,
`demo_parent` (parent of Ava Rivera, S-100), `other_parent` (parent of Mia
Chen, S-200), `demo_student` (is Ava Rivera).

### Running the tests

```bash
python manage.py test
```

### Continuous integration

`.github/workflows/tests.yml` runs the test suite on every push to `main`
and every pull request (Python 3.11 and 3.12).

## Configuration

Set these via environment variables in production:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Cryptographic signing key — any long random string |
| `FIELD_ENCRYPTION_KEY` | Key for encrypted fields — generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `DEBUG` | `false` in production |
| `FORCE_HTTPS` | `true` in production, once behind a reverse proxy that terminates TLS |
| `DATABASE_URL` | Postgres/MySQL connection string; falls back to SQLite if unset |
| `MAX_FAILED_ATTEMPTS` / `LOCKOUT_WINDOW_MINUTES` | Login lockout thresholds (defaults: 5 attempts / 15 minutes) |

`FIELD_ENCRYPTION_KEY` must stay the same across restarts and deploys once
there's encrypted data you care about — rotating it makes existing
encrypted rows unreadable.

## Deploying to Render

`requirements.txt`, `build.sh`, and `render.yaml` are already set up for
Render.

**Option A — Blueprint (one click):**

1. Push this project to a GitHub repo.
2. In the Render dashboard: **New → Blueprint**, and pick that repo.
   `render.yaml` describes both a web service and a free Postgres database.
3. Paste in a `FIELD_ENCRYPTION_KEY` when prompted (generate one with the
   command above — `SECRET_KEY` is generated for you automatically).
4. Deploy. Render builds with `build.sh` and starts the service with
   Gunicorn.
5. Seed demo data from the service's **Shell** tab in the Render dashboard:
   ```bash
   python manage.py seed_demo_data
   ```

**Option B — manual web service:**

1. **New → Web Service**, connect the repo.
2. Build command: `./build.sh`
3. Start command: `gunicorn config.wsgi:application`
4. Set the environment variables listed above (`DATABASE_URL` only if
   attaching a database — otherwise it falls back to SQLite, which works
   for a demo but resets on every deploy since Render's disk isn't
   persistent by default).
5. Deploy.

`ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` pick up Render's
`RENDER_EXTERNAL_HOSTNAME` automatically, so the default `*.onrender.com`
domain works without extra configuration. Add a custom domain the usual way
via the `ALLOWED_HOSTS` environment variable.

## License

MIT — see [LICENSE](LICENSE).
