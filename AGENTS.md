# AGENTS.md

Dokumentiert, wie wir KI-Coding-Agents in diesem Projekt einsetzen, und gibt Agents die
Regeln, an die sie sich halten müssen. Jedes Teammitglied ergänzt während der eigenen Arbeit
den Abschnitt "Einsatzprotokoll".

## Regeln für Agents (verbindlich)

1. **Architektur:** `domain/` importiert nur die Standardbibliothek. `application/` kennt
   weder SQLAlchemy noch FastAPI. Infrastruktur nur über die Protocols in
   `application/repositories.py` und `application/clock.py`.
2. **Keine Service-zu-Service-Imports.** Orchestrierung nur in `interfaces/api/`.
3. **Zeit nur über `Clock`.** Kein `datetime.now()`/`date.today()` in `domain/` oder
   `application/`. In Tests immer `FakeClock`.
4. **TDD:** Erst ein fehlschlagender Test, dann Produktionscode. Unit-Tests nutzen
   `tests/fakes.py` (keine DB, kein FastAPI).
5. **Spec first:** `docs/specs/<service>.md` existiert, bevor der Service implementiert wird.
   Entscheidungen zu offenen Edge Cases gehören in die Spec.
6. **Gemeinsame Dateien** (siehe README, "Branching-Strategie") nicht ohne Rückfrage ändern.
   Ist eine Protocol-Erweiterung nötig, sagt der Agent, was und warum, und ergänzt einen Test
   im Repository-Contract-Test.
7. **Kleine Commits** im Conventional-Commits-Format nach jedem abgeschlossenen Schritt.
8. **Vor jedem Commit grün:** `pytest -m "not integration"`, `ruff check .`,
   `ruff format --check .`, `mypy` (bzw. `npm test && npm run lint` im Frontend).
9. Bei Unklarheiten eine einfache, dokumentierte Variante vorschlagen statt zu raten oder
   lange nachzufragen.

## Eingesetzte Werkzeuge

| Werkzeug | Modell | Einsatz |
|---|---|---|
| Claude Code (VS Code Extension) | Claude Opus 5.5 | Fundament, Services, Tests, Doku |

Die verwendeten Prompts liegen im Team-Dokument "Padel-Court-Booking mit Warteliste – Claude
Code Prompts" (Foundation-Prompt + 4 Service-Prompts).

## Einsatzprotokoll

### Fundament (`feature/foundation`, 2026-10-01)

**Prompt:** Foundation-Prompt (Schritte 1–13).

**Vom Agent vor dem Start aufgezeigte Unklarheiten, vom Team entschieden:**
- Warteliste: Eintrag beim Nachrücken behalten und `notified_at` setzen, statt ihn zu löschen
  (der Prompt verlangte beides gleichzeitig).
- Buchungslimit: Nur Buchungen für Slots zählen, die noch nicht begonnen haben. Sonst würden
  gespielte CONFIRMED-Buchungen ein Mitglied für immer blockieren.
- Zahlungsfrist: `min(created_at + 12h, Slot-Start)`.
- Foundation-Arbeit auf eigenem Branch statt direkt auf `main`.

**Vom Agent getroffene Entscheidungen (zur Review):**
- Preisformel (40/60 CHF pro Stunde, Peak Mo–Fr ab 17:00 bis 22:00 und ganztags am
  Wochenende, Premium −20 %). Siehe `application/pricing.py`.
- Doppelbuchungsschutz: Service-Check + Partial Unique Index (ADR 001).
- Zusätzliche Exceptions `NotFoundError`, `NotAuthorizedError`, `InvalidPaymentError` und
  Basisklasse `DomainError`, damit die Service-Branches `exceptions.py` nicht gleichzeitig
  ändern müssen.
- Gemeinsame Helfer, die mehrere Services brauchen: `booking_limits.py`, `split_evenly`,
  `Booking.payment_deadline`.
- Fakes speichern Kopien, damit ein vergessenes `repository.update()` schon im Unit-Test
  auffällt. Ein Contract-Test prüft Fakes, SQLite und Postgres mit denselben Fällen.
- Zentrales Mapping Domain-Exception → HTTP-Status in `interfaces/api/errors.py`.

**Korrekturen während der Arbeit:** Der Agent fand selbst, dass `Session.begin_nested()`
ausstehende Änderungen *vor* dem SAVEPOINT flusht. Beim Booking-Update wäre eine
Constraint-Verletzung dadurch nicht sauber abgefangen worden. Die Mutation passiert jetzt
innerhalb des Savepoints. Das abgedeckte Szenario steht in
`test_reactivating_a_booking_on_a_taken_slot_is_rejected`.

<!--
Vorlage für weitere Einträge:

### <Use Case> (`feature/<branch>`, <Datum>, <Name>)
**Prompt:** ...
**Was der Agent gut gemacht hat:** ...
**Wo wir korrigieren mussten:** ...
**Protocol-/Shared-File-Änderungen (mit Begründung):** ...
-->

## Betrieb: periodische Jobs

_Wird mit SplitPayment ergänzt: wie `expire_stale_bookings` in Produktion ausgelöst wird._
