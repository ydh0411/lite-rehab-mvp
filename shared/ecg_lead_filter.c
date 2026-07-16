#include "ecg_lead_filter.h"

#include <stddef.h>

void ecg_lead_filter_init(ecg_lead_filter_t *filter, uint32_t now_ms)
{
    if (filter == NULL) return;
    filter->candidate_since_ms = now_ms;
    filter->stable_leads_off = true;
    filter->candidate_leads_off = true;
}

bool ecg_lead_filter_update(ecg_lead_filter_t *filter, bool raw_leads_off,
                            uint32_t now_ms)
{
    if (filter == NULL) return true;

    if (raw_leads_off != filter->candidate_leads_off) {
        filter->candidate_leads_off = raw_leads_off;
        filter->candidate_since_ms = now_ms;
    } else if (filter->stable_leads_off != filter->candidate_leads_off &&
               now_ms - filter->candidate_since_ms >= ECG_LEAD_DEBOUNCE_MS) {
        filter->stable_leads_off = filter->candidate_leads_off;
    }
    return filter->stable_leads_off;
}
