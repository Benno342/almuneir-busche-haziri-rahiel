# Padel Court Booking

Enterprise-grade Padel-Court-Buchungsplattform mit Warteliste und geteilter Bezahlung.
FHNW-Capstone "AI-assisted Coding". FastAPI + React, Clean Architecture, TDD.

Ein Club vermietet Courts. Mitglieder buchen Slots, zahlen ihren Anteil, stornieren und rücken
von der Warteliste nach.

## Architektur

```
backend/padel/
├── domain/              Entities (Dataclasses) + Exceptions, nur Standardbibliothek
├── application/         Use Cases und Ports, kennt weder SQLAlchemy noch FastAPI
│   ├── clock.py           Clock-Protocol (Zeit nie via datetime.now())
│   ├── pricing.py         PricingPolicy + split_evenly
│   ├── repositories.py    Repository-Protocols für alle 6 Entities
│   ├── booking_limits.py  gemeinsame Regel "max. 2 aktive Buchungen"
│   ├── join_waitlist.py   einfache Warteliste-Anmeldung
│   └── services/          die 4 Use-Case-Services (je 1 pro Teammitglied)
├── infrastructure/      SystemClock, SQLAlchemy-Modelle/-Repositories, Alembic-Migrationen
└── interfaces/api/      FastAPI: Routers, Pydantic-Schemas, DI, Fehler→HTTP, Orchestrierung
```

Abhängigkeiten zeigen nur nach innen: `interfaces → application → domain`, und
`infrastructure` implementiert die Protocols aus `application`.

**Services importieren sich nie gegenseitig.** Wenn ein Use Case einen anderen auslöst (nach
Cancel oder nach Ablauf einer Zahlung rückt die Warteliste nach), bekommt der API-Endpoint
beide Services injiziert und ruft sie nacheinander auf. Der erste Service meldet dafür nur
zurück, dass der Slot frei wurde.

**Transaktionen:** Ein Request entspricht einer DB-Transaktion (`get_session` in
`interfaces/api/dependencies.py`). Repositories flushen, committen aber nie. Bei einer
Exception wird alles zurückgerollt.

| Entity | Wichtigste Felder |
|---|---|
| Member | name, email, membership_tier (STANDARD/PREMIUM), joined_at |
| Court | name, indoor |
| TimeSlot | court_id, date, start_time, end_time (unique: court + date + start) |
| Booking | time_slot_id, booked_by_member_id, status, total_price, created_at, confirmed_at |
| Participant | booking_id, member_id, share_amount, paid, paid_at |
| WaitlistEntry | time_slot_id, member_id, position, created_at, notified_at |

Wichtige Entscheidungen:
- [ADR 001: Doppelbuchungsschutz](docs/adr/001-double-booking.md)
- [Querschnittsentscheidungen für alle Specs](docs/specs/README.md) (Zeitzonen, Buchungslimit,
  Zahlungsfrist, Warteliste)
- Preisformel: siehe Docstring in [pricing.py](backend/padel/application/pricing.py)

## Lokales Setup

Voraussetzungen: Python 3.12, Node 22, Docker.

```bash
# Datenbank (Postgres mit den DBs "padel" und "padel_test")
docker compose up -d

# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL=postgresql://padel:padel@localhost:5432/padel   # ohne: SQLite ./padel.db
alembic upgrade head
uvicorn padel.interfaces.api.main:create_app --factory --reload    # http://localhost:8000/docs

# Frontend
cd frontend
npm install
npm run dev                                                         # http://localhost:5173
```

Umgebungsvariablen: `DATABASE_URL` (Backend), `CORS_ORIGINS` (Backend, kommasepariert,
Default `http://localhost:5173`), `VITE_API_URL` (Frontend, Default `http://localhost:8000`).

## Tests

```bash
cd backend
pytest -m "not integration"            # schnell: Fakes, SQLite, API (wie CI-Job "backend-unit")
TEST_DATABASE_URL=postgresql://padel:padel@localhost:5432/padel_test \
  pytest -m integration                # gegen echten Postgres (wie CI-Job "backend-integration")
pytest --cov                           # alles + Coverage (Minimum 85 %)
ruff check . && ruff format --check . && mypy

cd frontend
npm test && npm run lint && npm run build
```

Test-Bausteine für alle Services:
- `tests/fakes.py`: `FakeClock` und In-Memory-Repositories (inkl. Doppelbuchungs-Constraint)
- `tests/builders.py`: `add_member`, `add_slot`, `add_booking`, ... für Testdaten
- Fixtures in `tests/conftest.py`: `clock`, `fake_repos`, `sqlite_engine`, `postgres_engine`
- Fixtures in `tests/api/conftest.py`: `client` (TestClient mit SQLite + FakeClock), `seed`
- `tests/repositories/test_repository_contract.py`: stellt sicher, dass Fakes, SQLite und
  Postgres sich gleich verhalten. Bei einer neuen Repository-Methode hier einen Test ergänzen.

## Branching-Strategie

- `main` ist geschützt. Merge nur per Pull Request mit grüner CI und mindestens einem Review.
- Ein Feature-Branch pro Use Case und Person:
  `feature/book-court`, `feature/cancel-booking`, `feature/promote-waitlist`,
  `feature/split-payment`.
- Reihenfolge pro Branch: Spec (`docs/specs/<service>.md`) → Unit-Tests → Service →
  API-Tests → Endpoint. Commits im Conventional-Commits-Format (`feat:`, `test:`, `docs:`,
  `fix:`, `ci:`, ...).
- **Gemeinsame Dateien** (`domain/`, `application/clock.py`, `pricing.py`, `repositories.py`,
  `booking_limits.py`, `infrastructure/db/`, Migrationen, `tests/fakes.py`, `tests/builders.py`,
  CI) nur nach Absprache im Team ändern, am besten in einem kleinen eigenen PR, den alle
  rebasen. Neue Migrationen immer auf dem aktuellen `main` erzeugen, sonst entstehen zwei
  Alembic-Heads.
- Erwartbare kleine Merge-Konflikte: `interfaces/api/main.py` (`include_router`) und
  `domain/exceptions.py`. Einfach beide Seiten übernehmen.

## Deployment (Render)

Geplant: Web Service für das Backend (Build `pip install ./backend`, Start
`alembic upgrade head && uvicorn padel.interfaces.api.main:create_app --factory --host 0.0.0.0 --port $PORT`),
Managed Postgres (dessen `postgres://`-URL wird automatisch auf `postgresql+psycopg://`
normalisiert) und eine Static Site für `frontend/dist`. Noch nicht eingerichtet.
