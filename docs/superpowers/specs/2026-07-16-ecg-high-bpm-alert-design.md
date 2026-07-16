# ECG High-BPM Alert Design

## Goal

Replace the current consecutive-BPM-difference alarm with a high-heart-rate
alarm that is resistant to isolated ECG spikes. The receiver buzzer must only
be requested after the filtered BPM has remained above 150 BPM for three
consecutive valid measurements.

LiteRehab remains a classroom engineering prototype, not a medical device.
The filtering and alarm rules improve demo stability but do not constitute a
clinically validated heart-rate measurement.

## Selected approach

Use a robust RR-interval detector within the existing portable `ecg_logic`
module. This is preferred over merely changing the old 20 BPM delta threshold,
which would continue to accept noise spikes, and over adding a full adaptive
ECG DSP pipeline, which would require labelled waveform data and hardware
calibration outside the current scope.

## Beat and BPM processing

1. A threshold crossing is a candidate beat only when the leads are stable and
   the ADC sample is not at either rail.
2. The first accepted candidate records its timestamp but does not produce a
   BPM value.
3. Candidate intervals outside the configured valid RR range are rejected as
   noise and do not update the displayed BPM or alarm state.
4. The detector stores the five most recent valid RR intervals and calculates
   BPM from their median. During startup, it uses the median of the valid
   intervals available so far.
5. The existing refractory period remains a first-line duplicate-peak guard;
   RR validation and median filtering provide the additional protection needed
   against isolated 200+ BPM spikes.

The detector retains threshold latch release when the signal returns below the
threshold. ADC rail samples (`0` and `4095`) are treated as invalid signal
samples and cannot create beats or alarms.

## Lead stability

A single lead-off sample must not repeatedly reset and restart the detector.
The receiver monitor debounces the digital lead-off inputs before passing a
stable lead state into `ecg_logic`. Detection resumes only after the connected
state has remained stable for the configured debounce interval. A confirmed
lead disconnection resets beat history, high-BPM confirmation state, and the
alarm latch.

## High-BPM state machine

- High threshold: strictly greater than 150 BPM.
- Confirmation: three consecutive filtered BPM measurements above 150 BPM.
- Alert behavior: emit one `high_bpm_alert` event when the third consecutive
  high measurement is accepted.
- Latched behavior: sustained high BPM does not emit additional alert events.
- Rearm threshold: at or below 140 BPM.
- Rearm confirmation: three consecutive filtered measurements at or below
  140 BPM.
- Values between 140 and 150 BPM preserve the current latch/counter state and
  cannot trigger or rearm the alarm by themselves.
- Invalid samples and rejected candidate beats never increment high or recovery
  counters.

The 10 BPM separation between trigger and rearm thresholds prevents repeated
alarms when the filtered value fluctuates around 150 BPM.

## Buzzer behavior

`app_main` requests the ECG buzzer pattern only for `high_bpm_alert`; the
legacy consecutive-change flag no longer controls the buzzer. The output layer
coalesces ECG alerts so an alert already queued or playing cannot be queued
again. Motion success and warning feedback retain their existing behavior and
continue to share the serialized output task.

The ECG alert remains the existing five 50 ms, 1000 Hz pulses separated by
50 ms gaps. Completing an ECG pattern clears the ECG-pending state.

## Telemetry compatibility

The ECG serial record exposes the high-BPM event explicitly as
`high_bpm_alert`. Python accepts both the new record and the previous
`rapid_change` schema so previously recorded sessions remain readable. New
session files use the explicit high-BPM field and do not interpret an old
rapid-change event as a high-heart-rate alarm.

## Verification

Host tests must demonstrate:

- the first candidate beat produces no BPM;
- rail samples cannot create a beat or alert;
- an isolated short RR interval cannot create a 200+ BPM output;
- median RR filtering rejects a single interval spike;
- one or two values over 150 BPM do not alert;
- the third consecutive filtered value over 150 BPM alerts exactly once;
- sustained high BPM does not repeat the alert;
- three filtered values at or below 140 BPM rearm the alert;
- confirmed lead-off resets BPM history and alarm state;
- an ECG alert already queued or playing is not duplicated;
- old and new ECG telemetry records both parse correctly.

Run the complete host C and Python test suites, then build the receiver firmware.
Hardware verification must separately confirm stable electrode contact, a
non-saturated waveform, plausible BPM during rest and movement, one alert for a
sustained test condition, and silence for isolated signal artifacts.
