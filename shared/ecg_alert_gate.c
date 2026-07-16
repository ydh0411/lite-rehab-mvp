#include "ecg_alert_gate.h"

#include <stddef.h>

void ecg_alert_gate_init(ecg_alert_gate_t *gate)
{
    if (gate == NULL) return;
    atomic_init(&gate->pending, false);
}

bool ecg_alert_gate_try_acquire(ecg_alert_gate_t *gate)
{
    if (gate == NULL) return false;
    return !atomic_exchange(&gate->pending, true);
}

void ecg_alert_gate_release(ecg_alert_gate_t *gate)
{
    if (gate == NULL) return;
    atomic_store(&gate->pending, false);
}
