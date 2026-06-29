<p align="center">
  <img src="https://img.shields.io/badge/CRITs-Threat%20Intelligence-blue?style=for-the-badge" alt="CRITs">
</p>

<h1 align="center">CRITs</h1>

<p align="center">
  <strong>Collaborative Research Into Threats — a web-based malware and threat-intelligence platform (Python 3 fork)</strong>
</p>

<p align="center">
  <a href="https://github.com/seifreed/crits/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python Versions">
  <img src="https://img.shields.io/badge/django-MongoEngine-092e20?style=flat-square&logo=django&logoColor=white" alt="Django + MongoEngine">
  <img src="https://img.shields.io/badge/docker-compose-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
</p>

<p align="center">
  <a href="https://github.com/seifreed/crits/stargazers"><img src="https://img.shields.io/github/stars/seifreed/crits?style=flat-square" alt="GitHub Stars"></a>
  <a href="https://github.com/seifreed/crits/issues"><img src="https://img.shields.io/github/issues/seifreed/crits?style=flat-square" alt="GitHub Issues"></a>
  <a href="https://buymeacoffee.com/seifreed"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-yellow?style=flat-square&logo=buy-me-a-coffee&logoColor=white" alt="Buy Me a Coffee"></a>
</p>

---

## Overview

**CRITs** (Collaborative Research Into Threats) is a web-based tool that combines an analytic engine with a cyber-threat database. It serves as a repository for attack data and malware, and gives analysts a platform for conducting and correlating malware analyses and for targeting data. CRITs structures threat information into top-level objects (TLOs) and lets analysts **pivot** across related content through relationships.

This repository is a **modernized Python 3 fork** of the original [crits/crits](https://github.com/crits/crits): the Python 2.7 codebase has been ported to Python 3, the dependency stack refreshed, and a Docker-based development workflow added. Legacy Py2 idioms and dead compatibility shims are removed rather than preserved.

### Key Features

| Feature | Description |
|---------|-------------|
| **Top-Level Objects** | Actors, Backdoors, Campaigns, Certificates, Domains, Emails, Events, Exploits, Indicators, IPs, PCAPs, Raw Data, Samples, Screenshots, Signatures, Targets |
| **Relationships & Pivoting** | Link TLOs to each other and pivot on metadata to discover related content |
| **Source-based RBAC** | Per-source access control — users only see data from sources they are granted |
| **Services Framework** | Pluggable analysis engines extend functionality out-of-tree |
| **REST API** | Tastypie-based API per TLO type (enabled via `ENABLE_API`) |
| **Binary Storage** | File blobs stored in GridFS or S3 |
| **Schema Migrations** | Per-document migration driven by `latest_schema_version` |
| **Docker Workflow** | One-command MongoDB + app via `docker compose` |

### Stack

```text
Backend       Django (MongoEngine ODM, not the Django ORM)
Database      MongoDB (GridFS for binaries)
Language      Python 3.11+
Dev runtime   Docker / docker-compose (MongoDB 7)
```

---

## Installation

### With Docker (Recommended)

```bash
git clone https://github.com/seifreed/crits.git
cd crits
docker compose up --build
```

This starts MongoDB and the CRITs app (on `http://localhost:8081`), generates the database config on first boot, and bootstraps default collections, roles, and indexes.

Create an admin user via environment variables:

```bash
CRITS_ADMIN_USER=admin CRITS_ADMIN_PASS='change-me' docker compose up --build
```

### From Source

```bash
git clone https://github.com/seifreed/crits.git
cd crits
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp crits/config/database_example.py crits/config/database.py   # edit Mongo settings
python manage.py create_default_collections
python manage.py create_indexes
```

### Quick Install Using Bootstrap

```bash
sh script/bootstrap
```

> Run `bootstrap` **once** — rerunning re-does the whole install. For the day-to-day dev server use `sh script/server`.

---

## Quick Start

```bash
# Day-to-day dev server (after first-time setup)
sh script/server

# Create an admin user
python manage.py users -R UberAdmin -u admin -p "pass" -s -i -a \
  -e a@b.c -f First -l Last -o org
```

---

## Usage

### Management Commands

| Command | Description |
|---------|-------------|
| `python manage.py create_default_collections` | Seed default collections (drop-protected) |
| `python manage.py create_indexes` | Create MongoDB indexes |
| `python manage.py create_roles` | Create default roles |
| `python manage.py create_default_dashboard` | Seed the default dashboard |
| `python manage.py setconfig` | Manage runtime configuration |
| `python manage.py upgrade` | Run per-document schema migrations |
| `python manage.py runscript` | Run a script against the CRITs context |
| `python manage.py find_corrupt_documents` | Report documents that fail to load (`--type <Type>`) |

### Running Tests

Tests use the Django test runner and switch the Mongo database to `crits-unittest` automatically. A local MongoDB must be running.

```bash
# In Docker (MongoDB service included)
docker compose run --rm -e CRITS_BOOTSTRAP=0 crits python manage.py test

# Single app / single test
python manage.py test crits.ips
python manage.py test crits.ips.tests.IPTests.test_name
```

---

## Configuration

- `DJANGO_SETTINGS_MODULE` = `crits.settings` (main settings in `crits/settings.py`).
- Local DB config: copy `crits/config/database_example.py` → `crits/config/database.py`.
- Optional overrides: copy `crits/config/overrides_example.py` → `crits/config/overrides.py`.
- Runtime app configuration lives in a Mongo `config` collection, wrapped by `crits/config/config.py` (`CRITsConfig`).

---

## Requirements

- Python 3.11+
- MongoDB (7.x recommended)
- See [requirements.txt](requirements.txt) for dependencies

---

## Acknowledgements

This project would not exist without the original **[CRITs](https://github.com/crits/crits)**, created and maintained by **MITRE** and the CRITs community. All credit for the original design — the TLO model, the relationship engine, the source-based access control, and the services framework — belongs to them.

This repository is an independent, community-maintained **Python 3 modernization fork** built on top of that work. Huge thanks to the original authors and contributors for releasing CRITs as open source.

- Original project: [github.com/crits/crits](https://github.com/crits/crits)
- Original website & docs: [crits.github.io](https://crits.github.io)

**Thanks for building CRITs!**

---

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Support the Project

If this project is useful in your workflows, you can support development:

<a href="https://buymeacoffee.com/seifreed" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50">
</a>

---

## License

This project is licensed under the MIT license. See [LICENSE](LICENSE).

**Attribution**
- Fork maintainer: **Marc Rivero López** | [@seifreed](https://github.com/seifreed)
- Repository: [github.com/seifreed/crits](https://github.com/seifreed/crits)
- Original project: **MITRE / the CRITs community** — [github.com/crits/crits](https://github.com/crits/crits)

---

<p align="center">
  <sub>Built for practical malware analysis and cyber threat-intelligence workflows</sub>
</p>
