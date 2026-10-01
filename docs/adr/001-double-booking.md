# ADR 001: Schutz gegen Doppelbuchungen

- **Status:** Akzeptiert
- **Datum:** 2026-10-01
- **Betrifft:** BookCourt, PromoteFromWaitlist (alle Stellen, die Bookings anlegen oder reaktivieren)

## Kontext

Ein TimeSlot darf zu jedem Zeitpunkt höchstens **eine aktive Buchung** haben. Aktiv heisst
Status `PENDING_PAYMENT` oder `CONFIRMED`. Stornierte (`CANCELLED`) und verfallene (`EXPIRED`)
Buchungen bleiben als Historie in der Tabelle und dürfen den Slot nicht blockieren.

Eine reine Prüfung im Service ("gibt es schon eine aktive Buchung?") genügt nicht. Zwei
gleichzeitige Requests können die Prüfung beide bestehen, bevor einer von ihnen schreibt
(Check-then-Insert-Race). Bei einer Club-App ist das realistisch: Ein frei gewordener
Abend-Slot wird oft von mehreren Mitgliedern gleichzeitig angeklickt. Zusätzlich legen zwei
Services Bookings an (BookCourt und PromoteFromWaitlist), die unabhängig voneinander
entwickelt werden.

## Optionen

1. **Nur Service-Check.** Einfach und datenbankunabhängig, aber nicht race-sicher.
2. **Normaler `UNIQUE(time_slot_id)` auf `bookings`.** Race-sicher, verbietet aber die
   Historie: Nach einer Stornierung könnte der Slot nie wieder gebucht werden.
3. **Pessimistisches Locking** (`SELECT ... FOR UPDATE` auf den TimeSlot). Race-sicher, aber
   jeder schreibende Pfad muss daran denken. SQLite kennt `FOR UPDATE` nicht, also verhielten
   sich Unit- und Produktionsumgebung unterschiedlich.
4. **Status-Wechsel auf dem TimeSlot** (z.B. `slot.is_booked`) mit optimistischem Locking.
   Dupliziert Zustand, der sich aus den Bookings ableiten lässt, und kann auseinanderlaufen.
5. **Service-Check + Partial Unique Index** auf `bookings(time_slot_id) WHERE status IN
   ('PENDING_PAYMENT', 'CONFIRMED')`.

## Entscheidung

Wir wählen **Option 5: zwei Verteidigungslinien**.

1. **Service-seitiger Check** (`BookingRepository.get_active_for_slot`): liefert im Normalfall
   eine verständliche Fehlermeldung (`SlotUnavailableError` → HTTP 409), ohne die DB-Exception
   zu provozieren.
2. **Partial Unique Index `uq_bookings_active_time_slot`** in der Datenbank (Migration `0001`):
   garantiert die Invariante auch bei Races und gegenüber jedem künftigen Code-Pfad.

`SqlBookingRepository.add/update` schreibt innerhalb eines SAVEPOINTs. Eine Verletzung dieses
Index wird dort abgefangen und als `SlotUnavailableError` geworfen. Für Services und API sehen
beide Verteidigungslinien gleich aus. Durch den SAVEPOINT wird nur der fehlgeschlagene Write
zurückgerollt, die restliche Transaktion des Requests bleibt nutzbar.

Die In-Memory-Fakes (`tests/fakes.py`) bilden denselben Constraint nach. Der
Repository-Contract-Test stellt sicher, dass Fake, SQLite und PostgreSQL sich identisch
verhalten.

## Konsequenzen

- ✅ Race-sicher auf PostgreSQL. Nachgewiesen durch `tests/integration/test_double_booking.py`:
  zwei Transaktionen prüfen beide "frei", die zweite scheitert beim Insert.
- ✅ Historie bleibt erhalten, ein stornierter Slot ist sofort wieder buchbar.
- ✅ Reaktivieren einer alten Buchung auf einem inzwischen belegten Slot wird ebenfalls verhindert.
- ✅ PostgreSQL und SQLite (≥ 3.8) unterstützen Partial Indexes. Die Unit-Tests gegen SQLite
  prüfen denselben Constraint.
- ⚠️ Nicht portabel auf MySQL (keine Partial Indexes). Ein DB-Wechsel bräuchte eine
  generierte Spalte oder Option 3.
- ⚠️ Das Prädikat ist als SQL-String an zwei Stellen hinterlegt (`models.py`,
  Migration `0001`). Eine Änderung der aktiven Status braucht eine neue Migration. Der Test
  `tests/integration/test_migrations.py` erkennt Abweichungen zwischen Modell und Migration.
- ⚠️ Beim Race erhält der Verlierer einen 409 erst beim Schreiben. Der Service muss deshalb vor
  der Booking keine anderen nicht-transaktionalen Seiteneffekte (z.B. E-Mails) auslösen.
  Seiteneffekte gehören nach den erfolgreichen Commit.
