#include <assert.h>
#include <stdio.h>

#include "ecg_lead_filter.h"

static void test_requires_stable_connection_for_200_ms(void)
{
    ecg_lead_filter_t filter;
    ecg_lead_filter_init(&filter, 0);

    assert(ecg_lead_filter_update(&filter, false, 0));
    assert(ecg_lead_filter_update(&filter, false, 199));
    assert(!ecg_lead_filter_update(&filter, false, 200));
}

static void test_transient_lead_off_does_not_disconnect(void)
{
    ecg_lead_filter_t filter;
    ecg_lead_filter_init(&filter, 0);
    assert(ecg_lead_filter_update(&filter, false, 0));
    assert(!ecg_lead_filter_update(&filter, false, 200));

    assert(!ecg_lead_filter_update(&filter, true, 210));
    assert(!ecg_lead_filter_update(&filter, false, 300));
    assert(!ecg_lead_filter_update(&filter, true, 400));
    assert(!ecg_lead_filter_update(&filter, true, 599));
    assert(ecg_lead_filter_update(&filter, true, 600));
}

static void test_reconnection_is_also_debounced(void)
{
    ecg_lead_filter_t filter;
    ecg_lead_filter_init(&filter, 1000);

    assert(ecg_lead_filter_update(&filter, false, 1100));
    assert(ecg_lead_filter_update(&filter, false, 1299));
    assert(!ecg_lead_filter_update(&filter, false, 1300));
}

int main(void)
{
    test_requires_stable_connection_for_200_ms();
    test_transient_lead_off_does_not_disconnect();
    test_reconnection_is_also_debounced();
    puts("test_ecg_lead_filter: PASS");
    return 0;
}
