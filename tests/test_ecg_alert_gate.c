#include <assert.h>
#include <stdio.h>

#include "ecg_alert_gate.h"

static void test_coalesces_until_current_alert_finishes(void)
{
    ecg_alert_gate_t gate;
    ecg_alert_gate_init(&gate);

    assert(ecg_alert_gate_try_acquire(&gate));
    assert(!ecg_alert_gate_try_acquire(&gate));
    ecg_alert_gate_release(&gate);
    assert(ecg_alert_gate_try_acquire(&gate));
}

static void test_null_gate_is_safe(void)
{
    ecg_alert_gate_init(NULL);
    assert(!ecg_alert_gate_try_acquire(NULL));
    ecg_alert_gate_release(NULL);
}

int main(void)
{
    test_coalesces_until_current_alert_finishes();
    test_null_gate_is_safe();
    puts("test_ecg_alert_gate: PASS");
    return 0;
}
