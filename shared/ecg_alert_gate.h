#ifndef LITE_REHAB_ECG_ALERT_GATE_H
#define LITE_REHAB_ECG_ALERT_GATE_H

#include <stdbool.h>
#include <stdatomic.h>

typedef struct {
    atomic_bool pending;
} ecg_alert_gate_t;

void ecg_alert_gate_init(ecg_alert_gate_t *gate);
bool ecg_alert_gate_try_acquire(ecg_alert_gate_t *gate);
void ecg_alert_gate_release(ecg_alert_gate_t *gate);

#endif
