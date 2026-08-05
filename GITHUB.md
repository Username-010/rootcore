# Publish RootCore on GitHub & deploy

## 1. Create an empty GitHub repo

1. Open [github.com/new](https://github.com/new)  
2. Name it e.g. **rootcore**  
3. Leave **without** README (this project already has one)  
4. Create repository  

## 2. Push from this folder

```bash
cd rootcore   # this directory

git init
git add .
git commit -m "RootCore: self-hosted plant care"

git branch -M main
git remote add origin https://github.com/YOURUSER/rootcore.git
git push -u origin main
```

SSH:

```bash
git remote add origin git@github.com:YOURUSER/rootcore.git
git push -u origin main
```

**Never commit `.env`** (gitignored). Only `.env.example`.

## 3. GitHub About box (suggested)

> Self-hosted plant care: smart watering, garden map, free photos, multi-home. Docker one-liner. No cloud required.

Topics: `plants` `self-hosted` `docker` `fastapi` `react` `gardening` `open-meteo` `homelab`

## 4. Deploy for others

```bash
git clone https://github.com/YOURUSER/rootcore.git
cd rootcore
cp .env.example .env
# SECRET_KEY=$(openssl rand -hex 32)
docker compose up -d --build
```

→ **http://localhost:8000**

## 5. Screenshots & docs in this repo

| Path | Content |
|------|---------|
| `README.md` | Features, themes, **API explanation**, screenshots |
| `docs/screenshots/` | Dashboard, plants, map, catalog, themes |
| `EXPORT.md` | Share / self-host notes |

## 6. APIs (summary for GitHub visitors)

| API | Key needed? | Purpose |
|-----|-------------|---------|
| Open-Meteo | No | Weather |
| MET Norway | No | Weather alternative |
| Wikimedia / Wikipedia | No | Plant photos |
| PlantNet | Free optional key | Photo identify |

All optional — core care works offline with your data only.
