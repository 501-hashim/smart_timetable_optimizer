# Smart Academic Timetable Optimizer — Deployment Guide

This guide describes how to deploy the **Smart Academic Timetable Optimizer** to a public HTTPS domain so faculty and staff can access it via a web link without running anything locally.

---

## Architecture Overview

- **Backend**: FastAPI (Python 3.12) running ASGI via `uvicorn` / `gunicorn`.
- **Frontend**: Single-Page Web Application served from `/static` and `/` with local vendor bundles (`React 18`, `Tailwind CSS`, `Babel`). Zero external CDN dependencies.
- **Database**: SQLAlchemy ORM with default persistent SQLite (`timetable.db`) or PostgreSQL.
- **File Exports**: In-memory streaming of Excel (`.xlsx` via `openpyxl`) and PDF (`.pdf` via `reportlab`). Cloud and container compatible.
- **Health Probes**: Available at `/health` and `/api/health`.

---

## 1. Environment Variables

Create a `.env` file in the root directory (refer to `.env.example`):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Set to `production` or `development`. |
| `DEBUG` | `false` | `false` disables Swagger UI and hides stack traces from public errors. |
| `SECRET_KEY` | *(Required in prod)* | 32+ character random string for security. |
| `PORT` | `8000` | Port for the web server (automatically set by Render/Railway/Heroku). |
| `HOST` | `0.0.0.0` | Host binding for network accessibility. |
| `DATABASE_URL` | `sqlite:///timetable.db` | Database URL. Supports PostgreSQL (`postgresql://...`). |
| `ALLOWED_ORIGINS` | `*` | Comma-separated list of allowed domains (e.g. `https://timetable.school.edu`). |
| `ALLOWED_HOSTS` | `*` | Comma-separated list of allowed HTTP Host headers. |

---

## 2. Deployment Options

### Option A: 1-Click Deploy on Render (Recommended)

1. Push this repository to **GitHub** or **GitLab**.
2. Go to [Render Dashboard](https://dashboard.render.com/) and click **New + Web Service**.
3. Connect your repository.
4. Render will automatically detect settings from `render.yaml`, or you can manually enter:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
5. In **Environment Variables**, set:
   - `ENVIRONMENT` = `production`
   - `DEBUG` = `false`
   - `SECRET_KEY` = *(click Generate)*
6. Click **Create Web Service**. Your app will be live at `https://your-app-name.onrender.com`.

---

### Option B: Deploy on Railway

1. Install the Railway CLI or connect via [Railway.app](https://railway.app/).
2. Click **New Project** → **Deploy from GitHub repo**.
3. Railway automatically detects the `Procfile` and `requirements.txt`.
4. Add environment variables:
   - `ENVIRONMENT=production`
   - `DEBUG=false`
5. Click **Generate Domain** under Settings.
6. The app will be accessible at your public Railway HTTPS link.

---

### Option C: Docker Container (Fly.io, AWS ECS, GCP Cloud Run, DigitalOcean)

Build and run the Docker image:

```bash
# Build the production image
docker build -t timetable-optimizer:latest .

# Run container locally on port 8000
docker run -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e DEBUG=false \
  timetable-optimizer:latest
```

Deploying to **Fly.io**:
```bash
fly launch
fly deploy
```

---

### Option D: Ubuntu / Linux VPS (Nginx + Systemd)

#### 1. Install System Dependencies
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx
```

#### 2. Clone and Setup Environment
```bash
git clone <your-repo-url> /var/www/timetable-optimizer
cd /var/www/timetable-optimizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your domain and production settings
```

#### 3. Setup Systemd Service
Create `/etc/systemd/system/timetable.service`:
```ini
[Unit]
Description=Smart Academic Timetable Optimizer
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/timetable-optimizer
EnvironmentFile=/var/www/timetable-optimizer/.env
ExecStart=/var/www/timetable-optimizer/venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable timetable
sudo systemctl start timetable
```

#### 4. Configure Nginx Reverse Proxy & SSL
Create `/etc/nginx/sites-available/timetable.conf`:
```nginx
server {
    server_name timetable.your-institution.edu;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and obtain free SSL via Let's Encrypt:
```bash
sudo ln -s /etc/nginx/sites-available/timetable.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d timetable.your-institution.edu
```

---

## 3. Verification & Health Check

After deployment, test the health check endpoint:

```bash
curl -f https://<your-deployed-domain>/health
```
Expected response:
```json
{
  "status": "healthy",
  "system": "Smart Academic Timetable Optimizer",
  "environment": "production",
  "version": "1.0.0"
}
```

Visit `https://<your-deployed-domain>` in any web browser to access the complete application.

---

## 4. Maintenance & Backups

- If using SQLite: Back up `/app/timetable.db` regularly using automated cron or persistent volumes.
- If using PostgreSQL: Leverage managed database automated backups (e.g. Supabase, Render Postgres, AWS RDS).
