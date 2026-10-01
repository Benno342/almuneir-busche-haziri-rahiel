# Specs

Eine Spec pro Use-Case-Service, geschrieben **bevor** der Service implementiert wird
(Spec-Driven Development). Erwartete Dateien:

| Spec | Service | Branch |
|------|---------|--------|
| `book-court.md` | `BookCourtService` | `feature/book-court` |
| `cancel-booking.md` | `CancelBookingService` | `feature/cancel-booking` |
| `promote-from-waitlist.md` | `PromoteFromWaitlistService` | `feature/promote-waitlist` |
| `split-payment.md` | `SplitPaymentService` | `feature/split-payment` |

## Vorlage

```markdown
# Spec: <Name>
## Zweck
## Input
## Output
## Regeln
## Edge Cases (müssen getestet werden)
## Akzeptanzkriterien
```

## Querschnittsentscheidungen (gelten für alle Specs)

Diese Punkte sind im Fundament umgesetzt. Bitte nicht in einer Spec abweichend definieren,
sondern bei Bedarf im Team ändern.

- **Zeit:** Services lesen die Zeit nur über `Clock.now()` (timezone-aware). Slot-Zeiten sind
  Wanduhrzeiten des Clubs (`Europe/Zurich`). Verglichen wird immer mit `TimeSlot.starts_at`.
- **Aktive Buchung:** Status `PENDING_PAYMENT` oder `CONFIRMED`. Höchstens eine pro Slot
  (ADR 001).
- **Buchungslimit (max. 2):** Es zählen nur aktive Buchungen für Slots, die **noch nicht
  begonnen** haben. Bereits gespielte CONFIRMED-Buchungen blockieren nicht. Gemeinsame
  Implementierung: `padel.application.booking_limits.has_reached_limit`.
- **Zahlungsfrist:** `Booking.payment_deadline(slot) = min(created_at + 12h, slot.starts_at)`.
  Eine Buchung kurz vor Spielbeginn verfällt also spätestens bei Spielbeginn.
- **Warteliste:** Einträge werden beim Nachrücken **nicht gelöscht**, sondern `notified_at`
  wird gesetzt. Wartend ist nur, wer `notified_at IS NULL` hat
  (`WaitlistRepository.list_waiting_for_slot`). Positionen werden nie wiederverwendet.
- **Preis:** `PricingPolicy.calculate_price(slot, tier)` mit dem Tier des **Buchenden**. Alle
  Teilnehmer teilen diesen Preis über `split_evenly`, die Rundungsdifferenz trägt der
  Buchende (erster Anteil).
- **Fehler → HTTP:** Neue Exceptions in `domain/exceptions.py` brauchen einen Eintrag in
  `interfaces/api/errors.py` (ein Test erzwingt das).
- **Keine Service-zu-Service-Imports.** Orchestrierung (Cancel → Promote, Expire → Promote)
  passiert nur in `interfaces/api/`.
