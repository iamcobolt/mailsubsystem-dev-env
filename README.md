# MailSubsystem Dev Environment

Local Docker development environment for
[MailSubsystem](https://github.com/iamcobolt/MailSubsystem).

This repo owns the contributor sandbox: PostgreSQL with pgvector, a local
Dovecot IMAP server, trusted local IMAP TLS certificates, and email import
helpers. It is meant to sit next to the core repo so MailSubsystem can stay
focused on the Rust application while still offering a one-command local setup.

## Quick Start

Clone both repos side by side:

```bash
git clone https://github.com/iamcobolt/MailSubsystem.git
git clone https://github.com/iamcobolt/mailsubsystem-dev-env.git
cd mailsubsystem-dev-env
make start
```

This creates `.env`, generates a local certificate authority and Dovecot server
certificate, and starts PostgreSQL plus Dovecot.

Create a sandbox `.env` in the core checkout:

```bash
make core-env
```

Then add an AI provider key to `../MailSubsystem/.env` and run the app from the
core repo:

```bash
cd ../MailSubsystem
make check
make app
```

## Import Test Mail

Export `.eml` files or an `.mbox` archive from your mail client, then import
them into the sandbox:

```bash
cd ../mailsubsystem-dev-env
make import EMAILS=~/path/to/exported-email
```

The sandbox IMAP account is:

| Setting | Value |
|---------|-------|
| IMAPS | `localhost:1993` |
| IMAP import port | `localhost:1143` |
| Username | `testuser` |
| Password | `testpass123` |

## Configuration

Run `make init` to create `.env` from `.env.example`, then edit it if your core
checkout is not in the default sibling location:

```env
MAILSUBSYSTEM_CORE_DIR=../MailSubsystem
MAILSUBSYSTEM_DB_PORT=15432
SANDBOX_IMAPS_PORT=1993
SANDBOX_IMAP_PORT=1143
```

`docker-compose.yml` mounts `schema.sql` from `MAILSUBSYSTEM_CORE_DIR` instead
of copying it into this repo. That keeps the database schema tied to the
MailSubsystem checkout you are testing.

### Environment Files

This repo has its own `.env` for Docker Compose and sandbox service wiring. It
does not configure the MailSubsystem Rust app directly.

| File | Owner | Purpose |
|------|-------|---------|
| `mailsubsystem-dev-env/.env` | Dev environment | Docker Compose ports, sandbox IMAP credentials, and the path to the MailSubsystem core checkout |
| `MailSubsystem/.env` | Core app | `IMAP_SERVER`, `IMAP_USERNAME`, `IMAP_PASSWORD`, `IMAP_TLS_CA_CERT_FILE`, `DATABASE_URL`, and AI provider keys |

Run `make core-env` when you want this repo to generate the app-facing sandbox
configuration in the core checkout.

## Commands

```bash
make start      # start PostgreSQL + Dovecot
make stop       # stop services, preserving volumes
make reset      # stop services, wipe volumes, and start fresh
make logs       # follow Docker logs
make ps         # show service status
make certs      # generate or refresh local trusted IMAP TLS certs
make core-env   # create ../MailSubsystem/.env for the sandbox
```

## TLS Behavior

The sandbox uses strict IMAP certificate validation. `make start` runs
`scripts/setup-trusted-certs.sh`, which creates:

- `dovecot/certs/ca.pem`
- `dovecot/certs/server.pem`
- `dovecot/certs/server.key`

Dovecot fails fast if those files are missing. That avoids falling back to an
untrusted self-signed certificate that MailSubsystem would correctly reject.

## Direct Docker Compose

The Make targets are the supported path because they create `.env` and TLS
certificates before Docker starts. If you use Docker Compose directly, run:

```bash
make init
docker compose --env-file .env -f docker-compose.yml --profile sandbox up -d --wait
```
