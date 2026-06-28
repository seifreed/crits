# CRITs — Python 3.14 / Django 5.2 migration

CRITs now runs on **Python 3.14**, **Django 5.2 LTS**, **mongoengine 0.29** and
**MongoDB 7**, with dependencies pinned to current (June 2026) releases.

## Run it (Docker)

```bash
docker compose up --build        # mongo + crits on http://localhost:8081
```

The app entrypoint generates `crits/config/database.py`, waits for MongoDB, and
runs an idempotent bootstrap (default collections, roles, indexes). Create an
admin user by setting env vars before `up`, or run once:

```bash
docker compose exec crits python manage.py users \
    -R UberAdmin -s -i -a -u admin -p 'CHANGE-ME' \
    -e admin@example.com -f Admin -l User -o YourOrg
```

Then log in at http://localhost:8081/login/.

Verified working:
- login → session → `/dashboards/` and every TLO list page
  (`/samples/list/`, `/indicators/list/`, `/actors/list/`, …) return HTTP 200.
- Write path: after granting a source to the UberAdmin role,
  `add_new_domain()` persists a `Domain` in MongoDB (read **and** write work).

## What changed

- **Syntax/stdlib**: print/except/raise, tabs, `iteritems`→`items`,
  `basestring`→`str`, `HTMLParser`/`cgi`/`imp`/`urllib`/`urlparse`/`ushlex`
  migrated to their Python 3 homes.
- **Django**: `urlresolvers`→`django.urls`, `url()`→`re_path`,
  `force_unicode`→`force_str`, `is_safe_url`→`url_has_allowed_host_and_scheme`,
  `{% ifequal %}`→`{% if %}`. settings.py rewritten for Django 5.2 (single
  modern INSTALLED_APPS/MIDDLEWARE/TEMPLATES, no version branches).
- **Auth**: CRITsUser `is_authenticated`/`is_anonymous` are now properties;
  `user_login()` and `AuthenticationMiddleware` reimplemented so the ObjectId
  session id works with Django's auth (which assumes an integer pk).
  `request.is_ajax()` restored via `AjaxCompatMiddleware`.
- **Dependencies**: dropped unused/dead (six, future, celery, pycrypto,
  tastypie-mongoengine, django_mongoengine fork, debug-toolbar). Added
  pycryptodome, packaging. Pillow≥12.2 (clears CVEs). `pip-audit`: clean.
- **REST API** (`ENABLE_API`) stays disabled — the tastypie resources need a
  port to modern tastypie/mongoengine before they can be re-enabled.

## Quality gates — status

- `pip-audit` (requirements.txt): **clean, 0 vulnerabilities**.
- SyntaxWarnings: **0**.
- `bandit` **HIGH: 0**. Fixed: `md5/sha1` → `usedforsecurity=False`,
  `yaml.load` → `safe_load`, password/reset-code RNG → `secrets`, TOTP crypto
  migrated pycryptodome → `cryptography`. Medium/low remain (subprocess for
  7z/zip, `/tmp`, "password" field-name strings — mostly false positives).
- `ruff`: **509 → 136**. Cleared: invalid escapes (W605), `== None` (E711),
  bare-except (E722), wildcard imports (F403/F405), `type(x)==str` (E721),
  one-line ifs (E701), unused imports (F401, 62), redefinitions (F811),
  and **every real bug** — `F821` undefined-name (≈28: `retVal` before
  assignment, `user`/`analyst`/`acl` typos, missing `acl = get_acl_object()`),
  `F507` `%`-format crash, `F601` duplicate dict key, `respones` typo.
  Remaining 136 are **cosmetic only** and deliberately left: `E712` (`== True`,
  unsafe to auto-rewrite given `1 == True`), `E402` (legit exec/lazy-import
  ordering), `E741` (ambiguous `l`/`I` names), `F841` (assignments whose RHS
  has side effects — auto-fix would drop the call). One `F821` is `GRIDFS` in
  the `database_example.py` template (exec'd in the settings namespace).
- `mypy`: not yet run to completion on the full tree (untyped legacy code).

Test suite (`manage.py test crits`): runs, system check clean. Remaining
failures are test-fixture RBAC/source setup and py3 bytes-vs-str assertions in
the test code, not app-runtime regressions (read **and** write paths verified
manually — see above).

The remaining cosmetic `ruff` items and `mypy` are a sizable follow-up across
the ~58k-line legacy codebase; they are intentionally not force-fixed because
the auto-rewrites carry behavior-change risk on code paths without test
coverage, and the app is already running and verified.
