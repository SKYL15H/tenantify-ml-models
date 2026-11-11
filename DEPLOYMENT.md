# 🚀 Tenantify AI — Deployment Guide (VPS / Self-Hosted)

## Prerequisites

Di VPS lo, pastikan udah ada:

- **Docker** ≥ 20.10
- **Docker Compose** ≥ 2.0
- **Git**
- **RAM minimal 4 GB** (model `BAAI/bge-m3` butuh ~2-3 GB)

---

## Quick Deploy (5 Menit)

### 1. Clone repo di VPS

```bash
ssh user@IP_VPS_LO

git clone https://github.com/USERNAME/REPO_NAME.git tenantify-api
cd tenantify-api
```

### 2. Setup environment

```bash
cp .env.example .env
# Edit kalau perlu ganti port
nano .env
```

### 3. Build & Run

```bash
# Build image (pertama kali ~10-15 menit karena download model bge-m3 ~2GB)
docker compose up -d --build

# Cek status
docker compose ps
docker compose logs -f tenantify-api
```

### 4. Verifikasi

```bash
# Tunggu sampai healthy (~1-2 menit setelah container start)
curl http://localhost:8000/health

# Buka Swagger UI
# http://IP_VPS_LO:8000/docs
```

---

## Expose ke Internet (Biar Frontend Bisa Tembak)

### Opsi A: Nginx Reverse Proxy (Recommended)

```bash
sudo apt install nginx -y
```

Buat config `/etc/nginx/sites-available/tenantify-api`:

```nginx
server {
    listen 80;
    server_name api.tenantify.com;  # Ganti dengan domain lo

    # Max upload size untuk batch comment moderation
    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (kalau nanti butuh)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeout buat request yang butuh proses lama (embedding)
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/tenantify-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Opsi B: HTTPS dengan Certbot (Gratis SSL)

Setelah Nginx jalan dan domain pointing ke IP VPS:

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.tenantify.com
```

Certbot otomatis update Nginx config dan renew SSL.

### Opsi C: Tanpa Domain (Direct IP)

Kalau belum punya domain, bisa langsung pakai IP:

```
http://IP_VPS_LO:8000/docs
http://IP_VPS_LO:8000/health
```

Pastikan port 8000 dibuka di firewall:

```bash
sudo ufw allow 8000/tcp
```

---

## Update Deployment

Kalau ada perubahan code:

```bash
cd tenantify-api
git pull origin main

# Kalau cuma berubah code (tanpa dependency baru)
docker compose up -d --build

# Kalau cuma update data JSON aja (ga perlu rebuild karena di-mount volume)
# Langsung aja replace file, auto-reload next request
```

---

## Useful Commands

```bash
# Lihat logs real-time
docker compose logs -f tenantify-api

# Restart service
docker compose restart tenantify-api

# Stop service
docker compose down

# Rebuild from scratch (kalau mau clean)
docker compose down
docker compose build --no-cache
docker compose up -d

# Masuk ke container
docker compose exec tenantify-api bash

# Cek resource usage
docker stats tenantify-api
```

---

## Troubleshooting

| Problem                      | Solution                                         |
| ---------------------------- | ------------------------------------------------ |
| Container OOMKilled          | Tambah RAM VPS jadi 4GB+ atau kurangi workers    |
| Build gagal (model download) | Cek koneksi internet VPS, retry build            |
| Port already in use          | Ganti PORT di `.env` atau stop service lama      |
| Slow first request           | Normal — model loading ~30-60 detik pertama kali |
| Data JSON ga ke-update       | Volume mount harusnya auto-sync, cek path        |

---

## API Base URL untuk Frontend

Setelah deploy, kasih URL ini ke tim Fullstack:

```
# Tanpa domain
http://IP_VPS:8000

# Dengan domain + SSL
https://api.tenantify.com

# Swagger/API Docs
https://api.tenantify.com/docs
```
