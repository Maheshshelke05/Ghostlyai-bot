# Deploying to production (Ubuntu 24.04 VPS)

Follow these steps in order on a fresh VPS. Everything after step 1 assumes you're SSH'd in.

## 1. Get a VPS and point DNS at it

- Ubuntu 24.04 LTS, 2 vCPU, 4 GB RAM, 50 GB disk (Mumbai / India region if available).
- Point an A record: `api.yourdomain.com` -> the server's IP.

## 2. Basic server security

```bash
adduser deploy
usermod -aG sudo deploy
# copy your SSH public key into /home/deploy/.ssh/authorized_keys, then:
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

sudo apt update && sudo apt install -y ufw unattended-upgrades
sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443
sudo ufw enable
sudo dpkg-reconfigure -plow unattended-upgrades
```

Log out and back in as `deploy` from here on.

## 3. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# log out and back in so the group membership takes effect
docker --version && docker compose version
```

## 4. Get the code

```bash
sudo mkdir -p /opt/job-bot && sudo chown $USER:$USER /opt/job-bot
git clone <your-repo-url> /opt/job-bot
cd /opt/job-bot
cp .env.example .env
nano .env   # fill in every value (see checklist below)
```

`.env` checklist:
- `APP_ENV=production`, `BASE_URL=https://api.yourdomain.com`
- `POSTGRES_PASSWORD` - long random string
- `DATABASE_URL` - `postgresql+asyncpg://jobbot:<same password>@postgres:5432/jobbot`
- `REDIS_URL=redis://redis:6379/0`
- `BOT_TOKEN` - from @BotFather
- `TELEGRAM_WEBHOOK_SECRET` - random 32+ chars, e.g. `openssl rand -hex 24`
- `SUPPORT_USERNAME`, `ADMIN_ALERT_CHAT_ID` - your own Telegram numeric id (message @userinfobot)
- `GEMINI_API_KEY`, `GEMINI_MODEL`
- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`
- `JWT_SECRET` - random 64+ chars, e.g. `openssl rand -hex 32`

## 5. SSL certificate

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d api.yourdomain.com
```

Add a renewal hook so nginx reloads after certbot renews (runs via certbot's own systemd timer):

```bash
echo '#!/bin/sh
cd /opt/job-bot/deploy && docker compose exec nginx nginx -s reload' | sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

Edit `deploy/nginx/default.conf` and replace `api.yourdomain.com` with your real domain if you
haven't already.

## 6. Start everything

```bash
cd /opt/job-bot/deploy
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.create_admin
```

## 7. Set up webhooks

- **Telegram**: the API sets its own webhook on startup (see `app/main.py` lifespan) when
  `APP_ENV=production` and `BOT_TOKEN` is set - nothing manual needed. Verify with:
  `curl "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"`.
- **Razorpay**: Dashboard -> Settings -> Webhooks -> Add new webhook:
  - URL: `https://api.yourdomain.com/webhooks/razorpay`
  - Secret: same value as `RAZORPAY_WEBHOOK_SECRET` in `.env`
  - Events: `payment_link.paid`, `payment_link.expired`, `payment_link.cancelled`

## 8. Backups

```bash
sudo mkdir -p /opt/backups
chmod +x /opt/job-bot/deploy/backup.sh
crontab -e
# add: 30 2 * * * /opt/job-bot/deploy/backup.sh >> /var/log/jobbot-backup.log 2>&1
```

Configure `rclone config` once (Google Drive / S3 / Backblaze) so the offsite copy step works.
Test a restore at least once before relying on it:
`gunzip -c jobbot-YYYY-MM-DD.sql.gz | docker compose exec -T postgres psql -U jobbot jobbot`.

## 9. Monitoring

- Add `https://api.yourdomain.com/health` to UptimeRobot / BetterStack, checked every 5 minutes.
- Optionally install Netdata for server resource monitoring: `curl -Ss https://my-netdata.io/kickstart.sh | sh`.

## Verify

```bash
curl https://api.yourdomain.com/health
# {"db":"ok","redis":"ok"}
```

Send `/start` to your bot on Telegram - you should get the language selection message.

## Update process

```bash
cd /opt/job-bot && git pull
cd deploy && docker compose build api worker
docker compose exec api alembic upgrade head   # only if a new migration was added
docker compose up -d api worker
docker compose logs -f --tail=100 api worker
```

## Rollback

```bash
cd /opt/job-bot && git log --oneline -5   # find the previous good commit
git checkout <previous-commit-sha>
cd deploy && docker compose build api worker && docker compose up -d api worker
# if the failing deploy included a migration: docker compose exec api alembic downgrade -1
```

## Reading logs

```bash
docker compose logs -f api        # API + Telegram webhook + admin API
docker compose logs -f worker     # digest, reminders, expiry, broadcasts
docker compose logs -f nginx
docker compose ps                 # container health at a glance
```
