#ifndef LITE_REHAB_ECG_LEAD_FILTER_H
#define LITE_REHAB_ECG_LEAD_FILTER_H

#include <stdbool.h>
#include <stdint.h>

#define ECG_LEAD_DEBOUNCE_MS 200u

typedef struct {
    uint32_t candidate_since_ms;
    bool stable_leads_off;
    bool candidate_leads_off;
} ecg_lead_filter_t;

void ecg_lead_filter_init(ecg_lead_filter_t *filter, uint32_t now_ms);
bool ecg_lead_filter_update(ecg_lead_filter_t *filter, bool raw_leads_off,
                            uint32_t now_ms);

#endif
