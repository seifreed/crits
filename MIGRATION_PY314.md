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

Verified working: login → session → `/dashboards/` and every TLO list page
(`/samples/list/`, `/indicators/list/`, `/actors/list/`, …) return HTTP 200.

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
- `ruff`: behavior-safe fixes applied; ~430 stylistic findings remain on legacy
  code (bare-except, `== None`, unused imports). Not yet zero.
- `bandit`: ~18 high (mostly `hashlib.md5` for file identification — needs
  `usedforsecurity=False`), plus medium/low. Not yet addressed.
- `mypy`: not yet run to completion on the full tree.

The remaining `ruff`/`bandit`/`mypy` cleanup is a sizable follow-up across the
~58k-line legacy codebase and is intentionally staged after getting the app
running and verified.
