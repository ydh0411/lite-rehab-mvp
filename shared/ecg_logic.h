#ifndef LITE_REHAB_ECG_LOGIC_H
#define LITE_REHAB_ECG_LOGIC_H

#include <stdbool.h>
#include <stdint.h>

#define ECG_THRESHOLD 2500
#define ECG_MIN_RR_MS 250u
#define ECG_MAX_RR_MS 2000u
#define ECG_RR_WINDOW_SIZE 5u
#define ECG_RR_WARMUP_COUNT 3u
#define ECG_HIGH_BPM_THRESHOLD 150.0f
#define ECG_REARM_BPM_THRESHOLD 140.0f
#define ECG_CONFIRM_COUNT 3u

typedef struct {
    uint32_t last_beat_ms;
    uint32_t rr_ms[ECG_RR_WINDOW_SIZE];
    float bpm;
    uint8_t rr_count;
    uint8_t rr_next;
    uint8_t high_count;
    uint8_t recovery_count;
    bool have_last_beat;
    bool beat_detected;
    bool alert_latched;
} ecg_logic_t;

typedef struct {
    bool leads_connected;
    bool beat;
    bool high_bpm_alert;
    float bpm;
} ecg_result_t;

void ecg_logic_init(ecg_logic_t *logic);
ecg_result_t ecg_logic_update(ecg_logic_t *logic, int raw_adc,
                              bool leads_off, uint32_t now_ms);

#endif
