#include "ecg_logic.h"

#include <math.h>
#include <string.h>

void ecg_logic_init(ecg_logic_t *logic)
{
    if (logic != NULL) {
        memset(logic, 0, sizeof(*logic));
    }
}

ecg_result_t ecg_logic_update(ecg_logic_t *logic, int raw_adc,
                              bool leads_off, uint32_t now_ms)
{
    ecg_result_t result = {0};
    if (logic == NULL) {
        return result;
    }

    if (leads_off) {
        ecg_logic_init(logic);
        return result;
    }

    result.leads_connected = true;
    result.bpm = logic->bpm;

    if (raw_adc <= ECG_THRESHOLD) {
        logic->beat_detected = false;
        return result;
    }

    const uint32_t delta_ms = now_ms - logic->last_beat_ms;
    if (logic->beat_detected || delta_ms <= ECG_REFRACTORY_MS) {
        return result;
    }

    logic->last_beat_ms = now_ms;
    logic->bpm = 60000.0f / (float)delta_ms;
    result.bpm = logic->bpm;
    result.beat = true;
    result.rapid_change =
        logic->last_bpm > 0.0f &&
        fabsf(logic->bpm - logic->last_bpm) > ECG_RAPID_CHANGE_BPM;
    logic->last_bpm = logic->bpm;
    logic->beat_detected = true;
    return result;
}
