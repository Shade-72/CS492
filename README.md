# School Management System (Django)

A single Django project that consolidates the whole team's Sprint 1 + Sprint 2
work. The original repo had the same product backlog implemented several
times over, in different frameworks, by different people: Flask blueprints,
a few FastAPI services, raw `sqlite3` scripts, and two `tkinter` desktop
scripts. This rebuilds it as one app, with one user model, one set of
database tables, and one access-control rule, so every story lives in
exactly one place instead of two or three inconsistent ones.

**I could not run this project in the sandbox that built it** — Django
isn't installed there and that environment has no PyPI access (unlike the
earlier Flask version, which used only pre-installed packages). Everything
below was written and reviewed carefully — syntax-checked, and every
`reverse()`/`{% url %}` call cross-checked against the URL configuration by
script — but it has **not been executed**. Run `python manage.py test`
yourself as the first step; if anything fails, share the traceback and I'll
fix it.

## What maps to what

| Story | Original file(s) / author | Now lives in |
|---|---|---|
| UMA-001 Role-Based User Accounts | Sprint 1 Flask `User`/`UserStore`; Carmen's FastAPI `User`/`Role` (TaskID4); Keiana's raw sqlite3 `users`/`roles`; `modules/uma/service.py` | `accounts/models.py` (`User.role`), Django's built-in auth |
| UMA-002 Secure Login | Sprint 1 Flask login/validators/auth/routes; Carmen's FastAPI login + JWT stub + tests (TaskID11); Carmen's RBAC matrix (TaskID5) | `accounts/views.py`, `validators.py`, `lockout.py`, `decorators.py` |
| UMA-003 Encrypt Data Storage | Keiana's Fernet `SENSITIVE_FIELDS` script; Carmen's encrypted `Student` model + tests (TaskID16) | `accounts/fields.py` (`EncryptedTextField`/`EncryptedCharField`), used by `User.phone_number` and `Student.ssn/home_address/medical_notes` |
| SIEM-004 Student Profile Enrollment | Carmen's `Sprint2_TaskID_1_code.py` | `academics/models.py` (`Student`), `views.enroll_student` |
| SIEM-005 Attendance Tracking | Carmen's `Sprint2_TaskID_2_code.py` (validation); Keiana's `KHTask3`/`KHTASK4` | `academics/forms.py` (`StudentEnrollmentForm`), `models.Attendance`, `views.record_attendance` |
| SIEM-006 Parent Record Access | `Parent portal.py`; Keiana's `KHTASK10` | `family_portal/views.py` (parent portal), `academics/views.student_grades` |
| AMG-007 Course Scheduling | Carmen's `Sprint2_TaskID_7_code.py` (**tkinter desktop app** — rewritten as a web form; Django has no desktop-GUI equivalent) | `academics/forms.ClassSectionForm` / `EnrollStudentInSectionForm`, `views.schedule_section` |
| AMG-008 Grade Entry | `Grade Entry UI` (HTML with no backend); Keiana's `KHTASK10` | `academics/forms.GradeForm`, `views.enter_grade` / `student_grades` |
| AMG-009 Report Card Generation | `Report cards.py` | `academics/report_cards.py`, `views.report_card` / `report_card_csv` |
| CNS-010 Announcements | `Announcements UI` (HTML with no backend) | `notices/models.Announcement`, `notices/views.py` |
| CNS-011 Parent Messaging | `Messaging.py`, `Messaging routes.py` | `family_portal/models.py` (`MessageThread`, `Message`), `family_portal/views.py` |
| CNS-012 Critical Notifications | `TASK14`; `Restrict critical alerts to admins only` (FastAPI JWT) | `notices/models.CriticalNotification`, `views.critical_notification_create`, reusing `accounts.decorators.role_required("admin")` |
| Sprint2 `TaskID_8` (assign teachers, prevent duplicates) | Carmen's tkinter script | Folded into `academics.forms.ClassSectionForm`'s conflict check |

## Design decisions worth knowing about

- **One user model, one login.** Django's own auth (`django.contrib.auth`)
  replaces three separate, incompatible attempts at authentication. Password
  hashing is Django's PBKDF2, not Flask's Werkzeug hashes or FastAPI's
  Passlib/bcrypt.
- **Encryption is transparent.** `accounts/fields.py` defines a Django model
  field that Fernet-encrypts on write and decrypts on read, so model and view
  code never calls `encrypt()`/`decrypt()` directly — unlike the two original
  attempts, which did it by hand. An encrypted field can't be used in an
  equality lookup (Fernet ciphertext is randomized), which is why `email` is
  left as an ordinary field and only `phone_number`, `ssn`, `home_address`,
  `medical_notes`, and message bodies are encrypted.
- **The tkinter scripts became web forms.** `Sprint2_TaskID_7_code.py` and
  `_8_code.py` were desktop GUI programs (`tkinter` + a button's `onclick`
  handler talking to sqlite3 directly). Django has no desktop-app concept, so
  their conflict-detection logic (a teacher, student, or room can't be
  double-booked) was ported to `academics/forms.py` as ordinary form
  validation, reachable from the browser instead of a desktop window.
- **RBAC is one decorator.** `accounts/decorators.role_required(*roles)`
  replaces Carmen's FastAPI `ROLE_MATRIX`/`check_role()`/`admin_required` JWT
  dependency and the scattered `if role == "admin"` checks in the Flask
  routes.
- **Anonymous access to a protected page redirects (302) rather than 401.**
  This is Django's normal `login_required` behavior. The original Flask
  `access.py` returned 401 JSON specifically for `/api/` paths; that
  API-vs-HTML branching wasn't carried over for simplicity. Say if you want
  it back — it's a small change to `accounts/decorators.py`.
- **In-memory cache for login lockout.** `accounts/lockout.py` uses Django's
  cache framework (`LocMemCache` by default). Swap in Redis via `CACHES` for
  a multi-process deployment; the lockout code doesn't change.

## Project layout

```
config/            settings, root urls, wsgi/asgi
accounts/          UMA-001/002/003: User model, login, RBAC, encryption, lockout
academics/         SIEM-004/005, AMG-007/008/009: students, attendance, grades,
                   scheduling, report cards
family_portal/     SIEM-006, CNS-011: parent record access, messaging
notices/           CNS-010/012: announcements, critical notifications
templates/         base.html, 403.html
static/css/        shared stylesheet
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

Migrations aren't included in this delivery (see the note at the top — I
couldn't run `makemigrations` myself without Django installed), so that's
the first thing to run.

### Running the tests

```bash
python manage.py test
```

### Continuous integration

`.github/workflows/tests.yml` runs `python manage.py check` and
`python manage.py test` on every push to `main` and every pull request
(Python 3.11 and 3.12).

## Production notes

- Set `SECRET_KEY`, `FORCE_HTTPS=true`, and `FIELD_ENCRYPTION_KEY` (generate
  with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
  via the environment. Without a `FIELD_ENCRYPTION_KEY`, an ephemeral key is
  generated each process start, so every encrypted value becomes unreadable
  after a restart — fine for local development, never for anything you
  intend to keep.
- Swap `DATABASES` from sqlite to Postgres/MySQL for anything beyond a demo
  (see **Deploying to Render** below — this is already wired up).
- Put the app behind a reverse proxy that terminates TLS and sets
  `X-Forwarded-Proto`; `FORCE_HTTPS=true` then makes `SecurityMiddleware`
  redirect any HTTP request to HTTPS.

## Deploying to Render

The project is ready for Render as-is: `requirements.txt` includes
`gunicorn` (the app server Render runs), `whitenoise` (serves collected
static files — CSS — without a separate web server), and `dj-database-url`
+ `psycopg` (so a Render Postgres database is picked up automatically). Two
files do the rest:

- **`build.sh`** — Render's build step: installs dependencies, runs
  `collectstatic`, and runs `migrate`.
- **`render.yaml`** — a Render "Blueprint": describes the web service *and*
  a free Postgres database in one file, so **New → Blueprint** in the Render
  dashboard, pointed at this repo, provisions both and wires
  `DATABASE_URL` from the database to the web service automatically.

### Option A: Blueprint (render.yaml) — one click

1. Push this project to a GitHub repo.
2. In the Render dashboard: **New → Blueprint**, pick that repo. Render reads
   `render.yaml` and shows you the web service + database it's about to
   create.
3. It will pause on `FIELD_ENCRYPTION_KEY` and ask you to paste one in
   (`SECRET_KEY` is auto-generated; a Fernet key has a specific format Render
   can't safely auto-generate for you — the field explains how to make one).
4. Deploy. Render runs `build.sh`, then starts the service with
   `gunicorn config.wsgi:application`.
5. Once it's live, run the demo-data seed against it from your own machine
   (Render's dashboard has a **Shell** tab for the service, or use `render
   ssh` from the CLI):
   ```bash
   python manage.py seed_demo_data
   ```

### Option B: Manual web service (no Postgres, or an existing database)

1. **New → Web Service**, connect the repo.
2. **Build Command**: `./build.sh`
3. **Start Command**: `gunicorn config.wsgi:application`
4. Under **Environment**, set:
   - `SECRET_KEY` — any long random string
   - `FIELD_ENCRYPTION_KEY` — from the command above
   - `DEBUG` — `false`
   - `FORCE_HTTPS` — `true`
   - `DATABASE_URL` — only if you're attaching a database; otherwise the app
     falls back to sqlite, which works for a demo but **resets on every
     deploy** since Render's disk isn't persistent by default.
5. Deploy.

### Things worth knowing

- **sqlite on Render is throwaway.** Without `DATABASE_URL` set, the app
  still runs, but every redeploy (and, on the free plan, every period of
  inactivity) gets a fresh empty database. Attach the Postgres add-on (or
  set `DATABASE_URL` to any Postgres/MySQL instance) for data that needs to
  survive.
- **Same for the rotating log file** (`logs/auth.log`). Render's console
  logs (Dashboard → your service → Logs) are the durable copy in
  production; the on-disk file is there for local debugging only.
- **`FIELD_ENCRYPTION_KEY` must stay the same across deploys** once you have
  encrypted data you care about — rotating it makes existing encrypted rows
  unreadable (the field tolerates that by returning the raw ciphertext
  instead of crashing, but the original value is gone). Set it once, in
  Render's environment settings, not just for one deploy.
- `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` pick up Render's
  `RENDER_EXTERNAL_HOSTNAME` (which Render sets for you) automatically —
  you don't need to set those yourself for the default `*.onrender.com`
  domain. Add a custom domain the normal Django way (`ALLOWED_HOSTS` env
  var) if you attach one.

## License

MIT — adapt freely for your own project.
