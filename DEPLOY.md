# Deploying WOODORA to Render

The database and image storage stay on Supabase; Render only runs the Django
app. Nothing about your Supabase project changes.

---

## 1. Push the code to GitHub

Render deploys from a Git remote, so the project needs one. `git init` has
already been run and everything is staged.

```bash
git commit -m "WOODORA catalogue: Django + Supabase Postgres"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

`.gitignore` keeps `.env`, `db.sqlite3`, `staticfiles/` and `media/` out of the
repo. **Verify `.env` is not in the push** — it holds your database password
and S3 secret:

```bash
git ls-files | grep -c "^\.env$"   # must print 0
```

## 2. Create the service

In the Render dashboard: **New → Blueprint**, select the repo. Render reads
`render.yaml` and fills in the runtime, build command, start command and
region (Singapore, nearest to your `ap-southeast-1` Supabase project).

Prefer clicking through instead? **New → Web Service** with:

| Field | Value |
|---|---|
| Runtime | Python 3 |
| Build command | `./build.sh` |
| Start command | `gunicorn woodora.wsgi:application` |
| Health check path | `/` |

## 3. Set the environment variables

`render.yaml` marks the secrets `sync: false`, so Render prompts for them
rather than reading them from the repo. Copy the values out of your local
`.env` — they are identical:

| Key | Notes |
|---|---|
| `DATABASE_URL` | **Keep the `%40`.** Your password contains `@`, which must stay percent-encoded or the connection fails. |
| `SUPABASE_URL` | `https://ryrcdevoigemlrwdhdnk.supabase.co` |
| `SUPABASE_BUCKET` | `product-images` |
| `SUPABASE_S3_ENDPOINT` | `.../storage/v1/s3` |
| `SUPABASE_S3_REGION` | `ap-southeast-1` |
| `SUPABASE_S3_ACCESS_KEY_ID` | from Supabase → Storage → S3 access keys |
| `SUPABASE_S3_SECRET_ACCESS_KEY` | same |
| `SECRET_KEY` | Blueprint generates one. Setting up by hand? Generate with `python -c "import secrets;print(secrets.token_urlsafe(64))"` — do **not** reuse the `django-insecure-` key from local. |
| `DEBUG` | `False` |

`ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` need no input: settings read
Render's `RENDER_EXTERNAL_HOSTNAME` automatically.

## 4. Deploy

Render runs `build.sh`: install → `collectstatic` → `migrate` →
`rebuild_search`. Migrations are already applied to your Supabase database, so
the first deploy's `migrate` is a no-op.

## 5. Create an admin user

Once live, open **Shell** on the service:

```bash
python manage.py createsuperuser
```

Then sign in at `https://<your-service>.onrender.com/admin/`.

---

## What was added for deployment

- **`gunicorn`** — the WSGI server; Django's `runserver` is not for production.
- **WhiteNoise** — serves static files from the app. Render has no separate
  static host, and with `DEBUG=False` Django stops serving them itself.
  `CompressedManifestStaticFilesStorage` fingerprints and gzips them
  (`style.49abe43224c2.css`) for far-future caching.
- **`STATIC_ROOT`** — where `collectstatic` writes; gitignored.
- **Security settings**, all inert while `DEBUG=True`: HTTPS redirect, HSTS,
  secure cookies, `nosniff`, `X-Frame-Options: DENY`, and
  `SECURE_PROXY_SSL_HEADER` so Django trusts Render's TLS-terminating proxy.
- **`MAILERS`** — Django 6.1 refuses to boot with `DEBUG=False` on a
  development email backend. This project sends no mail, so it falls back to
  the dummy backend with `mail.E001` deliberately silenced. **Admin password
  reset will not deliver.** Set `EMAIL_HOST`, `EMAIL_HOST_USER` and
  `EMAIL_HOST_PASSWORD` to switch to real SMTP; the silence lifts by itself.
- **`.gitattributes`** — forces LF endings on `build.sh`. A CRLF shell script
  fails on Linux with `bad interpreter: No such file or directory`.

## Things worth knowing

- **Free tier sleeps.** After 15 minutes idle the service spins down; the next
  request takes ~50s. Fine for a demo, not for real traffic.
- **Ephemeral disk.** Anything written to local disk is lost on redeploy. This
  does not affect product images — they live in Supabase Storage.
- **Use the session pooler** (port 5432) in `DATABASE_URL`, not the transaction
  pooler (6543). `conn_max_age=600` keeps connections open, which the
  transaction pooler does not support.
- **Region.** The app is in Singapore and the database in `ap-southeast-1`;
  keep them together or every query pays cross-region latency.
