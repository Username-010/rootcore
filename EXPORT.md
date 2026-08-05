# Sharing PlantPilot with others

PlantPilot is designed for **self-hosting**. Anyone with Docker/Podman (or Python + Node + Postgres) can run their own copy. Your plant data never has to leave their machine.

## What they need

| Item | Required? | Notes |
|------|-----------|--------|
| Docker **or** Podman + docker-compose | Recommended | Postgres in a container |
| Python 3.12+ + [uv](https://github.com/astral-sh/uv) | For dev start script | API |
| Node 20+ | For dev UI | Vite |
| **Open-Meteo** | Optional | Weather — **no API key** |
| **PlantNet** | Optional | Plant ID — free key from plantnet.org later |

## Publish on GitHub first

See **[GITHUB.md](./GITHUB.md)** for exact `git` + Docker steps you can paste into a new empty repo.

## Fastest path for a friend (development-style)

```bash
git clone https://github.com/YOURUSER/plantpilot.git
cd plantpilot
# Optional: copy and edit secrets
cp .env.example .env

# One command (Linux/macOS with Podman or Docker):
chmod +x scripts/plantpilot
./scripts/plantpilot start
# or: make start
```

Open **http://localhost:5173**

First visit: setup wizard (admin account + household + optional location).

Stop:

```bash
./scripts/plantpilot stop        # API + web
./scripts/plantpilot stop --all  # also Postgres
```

## Production-style (single port, easiest to replicate)

One image serves the SPA + API. Named volumes keep Postgres and plant photos across restarts.

```bash
cp .env.example .env
# Set SECRET_KEY to a long random value:
#   openssl rand -hex 32
docker compose up -d --build
# App: http://localhost:8000
```

With Podman:

```bash
systemctl --user enable --now podman.socket
export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/podman/podman.sock
docker-compose up -d --build
```

Reverse-proxy with Caddy/nginx using `deploy/Caddyfile.example` if you expose it on a home server.

### After first login

1. Complete the setup wizard (admin + household + optional lat/lon).
2. **Settings → Load demo garden** — sample plants + map with L/U-shaped beds.
3. Or add plants from **Catalog**, place them on **Map**, use **Freehand** to draw custom beds.

### Data that persists

| Volume | Contents |
|--------|----------|
| `plantpilot_pgdata` | Postgres database |
| `plantpilot_media` | Plant photos / labels |

`docker compose down` keeps volumes; use `docker compose down -v` only if you intend to wipe data.

## License

AGPL-3.0 — free to use and share; network services based on this code must provide source to users. See [LICENSE](./LICENSE).

## What to tell them about weather

- Set **latitude/longitude** in Setup or Settings.
- Uses **Open-Meteo** (free, no key). Coordinates are sent only to Open-Meteo when weather is fetched.
- Without coordinates, watering still works; outdoor weather factors stay off.
