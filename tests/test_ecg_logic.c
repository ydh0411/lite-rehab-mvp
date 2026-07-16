#include <assert.h>
#include <math.h>
#include <stdio.h>

#include "ecg_logic.h"

static void assert_close(float actual, float expected)
{
    assert(fabsf(actual - expected) < 0.01f);
}

static void test_threshold_crossing_and_latch_release(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);

    ecg_result_t first = ecg_logic_update(&logic, 2600, false, 300);
    assert(first.leads_connected);
    assert(first.beat);
    assert(!first.rapid_change);
    assert_close(first.bpm, 200.0f);

    ecg_result_t held = ecg_logic_update(&logic, 2700, false, 700);
    assert(!held.beat);

    ecg_result_t released = ecg_logic_update(&logic, 2400, false, 710);
    assert(!released.beat);

    ecg_result_t second = ecg_logic_update(&logic, 2600, false, 900);
    assert(second.beat);
    assert(second.rapid_change);
    assert_close(second.bpm, 100.0f);
}

static void test_refractory_interval_is_strictly_greater_than_250_ms(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);

    assert(ecg_logic_update(&logic, 2600, false, 300).beat);
    (void)ecg_logic_update(&logic, 2400, false, 310);
    assert(!ecg_logic_update(&logic, 2600, false, 550).beat);
    assert(ecg_logic_update(&logic, 2600, false, 551).beat);
}

static void test_rapid_change_requires_more_than_20_bpm(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);

    assert(ecg_logic_update(&logic, 2600, false, 600).beat);
    (void)ecg_logic_update(&logic, 2400, false, 610);

    ecg_result_t exactly_twenty = ecg_logic_update(&logic, 2600, false, 1350);
    assert(exactly_twenty.beat);
    assert_close(exactly_twenty.bpm, 80.0f);
    assert(!exactly_twenty.rapid_change);

    (void)ecg_logic_update(&logic, 2400, false, 1360);
    ecg_result_t over_twenty = ecg_logic_update(&logic, 2600, false, 1750);
    assert(over_twenty.beat);
    assert_close(over_twenty.bpm, 150.0f);
    assert(over_twenty.rapid_change);
}

static void test_lead_off_resets_stale_beat_history(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);

    assert(ecg_logic_update(&logic, 2600, false, 600).beat);
    ecg_result_t disconnected = ecg_logic_update(&logic, 2600, true, 700);
    assert(!disconnected.leads_connected);
    assert(!disconnected.beat);
    assert(!disconnected.rapid_change);
    assert_close(disconnected.bpm, 0.0f);

    ecg_result_t reconnected = ecg_logic_update(&logic, 2600, false, 2000);
    assert(reconnected.leads_connected);
    assert(reconnected.beat);
    assert(!reconnected.rapid_change);
}

int main(void)
{
    test_threshold_crossing_and_latch_release();
    test_refractory_interval_is_strictly_greater_than_250_ms();
    test_rapid_change_requires_more_than_20_bpm();
    test_lead_off_resets_stale_beat_history();
    puts("test_ecg_logic: PASS");
    return 0;
}
