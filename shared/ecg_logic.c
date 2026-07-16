#include "ecg_logic.h"

#include <string.h>

static uint32_t median_rr_ms(const ecg_logic_t *logic)
{
    uint32_t sorted[ECG_RR_WINDOW_SIZE] = {0};
    for (uint8_t index = 0; index < logic->rr_count; ++index) {
        sorted[index] = logic->rr_ms[index];
    }
    for (uint8_t index = 1; index < logic->rr_count; ++index) {
        const uint32_t value = sorted[index];
        uint8_t position = index;
        while (position > 0 && sorted[position - 1] > value) {
            sorted[position] = sorted[position - 1];
            --position;
        }
        sorted[position] = value;
    }
    return sorted[logic->rr_count / 2u];
}

static bool update_high_bpm_state(ecg_logic_t *logic)
{
    if (logic->bpm > ECG_HIGH_BPM_THRESHOLD) {
        logic->recovery_count = 0;
        if (logic->high_count < ECG_CONFIRM_COUNT) {
            ++logic->high_count;
        }
        if (logic->high_count == ECG_CONFIRM_COUNT && !logic->alert_latched) {
            logic->alert_latched = true;
            return true;
        }
    } else if (logic->bpm <= ECG_REARM_BPM_THRESHOLD) {
        logic->high_count = 0;
        if (logic->recovery_count < ECG_CONFIRM_COUNT) {
            ++logic->recovery_count;
        }
        if (logic->recovery_count == ECG_CONFIRM_COUNT) {
            logic->alert_latched = false;
        }
    } else {
        logic->high_count = 0;
        logic->recovery_count = 0;
    }
    return false;
}

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

    if (raw_adc <= 0 || raw_adc >= 4095) {
        return result;
    }

    if (raw_adc <= ECG_THRESHOLD) {
        logic->beat_detected = false;
        return result;
    }

    if (logic->beat_detected) {
        return result;
    }
    logic->beat_detected = true;

    if (!logic->have_last_beat) {
        logic->have_last_beat = true;
        logic->last_beat_ms = now_ms;
        result.beat = true;
        return result;
    }

    const uint32_t rr_ms = now_ms - logic->last_beat_ms;
    if (rr_ms < ECG_MIN_RR_MS) {
        return result;
    }
    if (rr_ms > ECG_MAX_RR_MS) {
        logic->last_beat_ms = now_ms;
        return result;
    }

    logic->last_beat_ms = now_ms;
    logic->rr_ms[logic->rr_next] = rr_ms;
    logic->rr_next = (uint8_t)((logic->rr_next + 1u) % ECG_RR_WINDOW_SIZE);
    if (logic->rr_count < ECG_RR_WINDOW_SIZE) {
        ++logic->rr_count;
    }
    result.beat = true;

    if (logic->rr_count < ECG_RR_WARMUP_COUNT) {
        return result;
    }

    logic->bpm = 60000.0f / (float)median_rr_ms(logic);
    result.bpm = logic->bpm;
    result.high_bpm_alert = update_high_bpm_state(logic);
    return result;
}
