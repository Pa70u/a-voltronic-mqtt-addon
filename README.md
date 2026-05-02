# GarageOS — Garage de la Montagne

Logiciel de gestion **devis / factures / parking** pour le Garage de la Montagne (94510 La Queue-en-Brie).

> ⚠️ Refonte en cours — branche `claude/rebuild-invoice-parking-app-8nFH3`. La version `main` contient un dump legacy à supprimer.

## Stack

- **Backend** : FastAPI 0.115 (Python 3.11) + SQLite (WAL)
- **Frontend** : HTML/CSS/JS — refactor en cours vers Alpine.js modulaire (jalon 6)
- **Reverse proxy** : nginx + Let's Encrypt
- **Paiements** : Stripe (Payment Links + webhook signé)
- **SMS** : Brevo
- **Email** : Gmail SMTP
- **Déploiement** : Docker Compose

## Démarrage local

```bash
cp .env.example .env
# remplir les valeurs .env (Gmail, Brevo, Stripe…)

docker compose up -d --build
```

L'API écoute sur `127.0.0.1:8000` (jamais exposée directement, nginx fait le proxy via `/api/`).

## Tests

```bash
cd backend
pip install -r requirements.txt
pip install pytest httpx
pytest tests/ -v
```

## Structure

```
.
├── backend/
│   ├── main.py              # API FastAPI (en cours de refactor → app/)
│   ├── schema.sql           # Schéma SQLite versionné
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
├── frontend/
│   └── index.html           # SPA monolithique (à découper jalon 6)
├── nginx/
│   └── nginx.conf
├── scripts/                 # Scripts de migration / import legacy
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Plan de refonte (option A — refactor progressif)

| # | Jalon | Statut |
|---|---|---|
| 1 | Setup branche + audit (CI, schema, tests fumée) | ✅ |
| 2 | Sécurité critique (bcrypt, Pydantic, signature webhook Stripe, CORS) | ⏳ |
| 3 | Refactor backend en modules (`app/auth`, `app/factures`, …) | ⏳ |
| 4 | Génération PDF factures + devis (reportlab) | ⏳ |
| 5 | Engagement 6 mois parking + relances automatiques (APScheduler) | ⏳ |
| 6 | Refactor frontend en pages + composants Alpine.js | ⏳ |

## Phase 2 (post-refonte)

- Ouverture portail (Shelly/Sonoff via MQTT)
- Caméras d'entrée + reconnaissance plaque (ALPR)
