# Motion Buzzer Valid-Repetition Design

## Goal

Make motion feedback audible only when the wearable confirms a new valid
repetition by increasing `rep_count`. Motion state transitions, fast attempts,
insufficient-range attempts, repeated packets, and stale packets must remain
silent. The confirmed ECG high-BPM alarm remains independent and unchanged.

## Selected approach

Use the monotonic repetition counter as the sole source of motion buzzer
events. The current `active -> idle` rule is removed because it represents an
attempt ending, not necessarily a valid repetition. Quality flags are still
displayed and recorded but no longer create motion tones.

## Feedback state

`feedback_logic_t` stores the greatest `rep_count` accepted during the current
BLE connection. The first packet establishes a silent baseline. A later packet
emits one `FEEDBACK_EVENT_SUCCESS` only when its counter is strictly greater
than the stored value, then stores the new value. Equal or lower counters are
silent and cannot lower the baseline, preventing duplicate tones from repeated
or stale packets.

When BLE disconnects, `app_main` reinitializes feedback state. The first packet
after reconnection is therefore silent even if the wearable rebooted and its
counter restarted from zero.

`FEEDBACK_EVENT_WARNING` remains in the shared enum for interface compatibility,
but motion packet processing no longer produces it. The existing receiver
output implementation does not need to change.

## ECG separation

The ECG path continues to request its five-pulse alert only after the filtered
BPM state machine confirms three measurements above 150 BPM. Motion feedback
changes do not suppress or alter this safety-demo alert.

## Documentation

README and demo instructions must state that only a counted valid repetition
produces the single 880 Hz motion tone. Fast, short-range, and incomplete
attempts remain visible on the OLED/dashboard and in telemetry but are silent.

## Verification

Host tests must demonstrate:

- the first packet is silent;
- state transitions without a counter increase are silent;
- fast and insufficient-range attempts without a counter increase are silent;
- one counter increase produces one success event;
- repeating the same increased count remains silent;
- a jump by more than one count produces only one success event;
- a lower stale count is silent and does not lower the stored baseline;
- resetting feedback state makes the next packet a silent baseline.

Run all host C tests, all Python tests, and build the receiver firmware. Flash
the receiver only after the software checks pass.
