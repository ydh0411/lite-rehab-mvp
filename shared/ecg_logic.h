#ifndef LITE_REHAB_ECG_LOGIC_H
#define LITE_REHAB_ECG_LOGIC_H

#include <stdbool.h>
#include <stdint.h>

#define ECG_THRESHOLD 2500
#define ECG_REFRACTORY_MS 250u
#define ECG_RAPID_CHANGE_BPM 20.0f

typedef struct {
    uint32_t last_beat_ms;
    float bpm;
    float last_bpm;
    bool beat_detected;
} ecg_logic_t;

typedef struct {
    bool leads_connected;
    bool beat;
    bool rapid_change;
    float bpm;
} ecg_result_t;

void ecg_logic_init(ecg_logic_t *logic);
ecg_result_t ecg_logic_update(ecg_logic_t *logic, int raw_adc,
                              bool leads_off, uint32_t now_ms);

#endif
