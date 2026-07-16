#ifndef LITE_REHAB_ECG_MONITOR_H
#define LITE_REHAB_ECG_MONITOR_H

#include <stdint.h>

#include "ecg_logic.h"
#include "esp_err.h"

typedef struct {
    uint32_t timestamp_ms;
    int raw_adc;
    ecg_result_t result;
} ecg_monitor_sample_t;

typedef void (*ecg_monitor_callback_t)(const ecg_monitor_sample_t *sample);

esp_err_t ecg_monitor_init(ecg_monitor_callback_t callback);

#endif
