#include <assert.h>
#include <math.h>
#include <stdio.h>

#include "ecg_logic.h"

static void assert_close(float actual, float expected)
{
    assert(fabsf(actual - expected) < 0.01f);
}

static ecg_result_t pulse(ecg_logic_t *logic, uint32_t now_ms)
{
    ecg_result_t result = ecg_logic_update(logic, 3000, false, now_ms);
    (void)ecg_logic_update(logic, 2200, false, now_ms + 10);
    return result;
}

static void test_requires_three_rr_intervals_before_publishing_bpm(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);

    assert_close(pulse(&logic, 1000).bpm, 0.0f);
    assert_close(pulse(&logic, 1400).bpm, 0.0f);
    assert_close(pulse(&logic, 1800).bpm, 0.0f);
    ecg_result_t ready = pulse(&logic, 2200);
    assert_close(ready.bpm, 150.0f);
    assert(!ready.high_bpm_alert);
}

static void test_median_rejects_one_short_interval_spike(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);

    (void)pulse(&logic, 1000);
    (void)pulse(&logic, 1400);
    (void)pulse(&logic, 1800);
    assert_close(pulse(&logic, 2200).bpm, 150.0f);
    assert_close(pulse(&logic, 2500).bpm, 150.0f);
}

static void test_interval_below_minimum_is_not_a_beat(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);

    assert(pulse(&logic, 1000).beat);
    assert(!pulse(&logic, 1200).beat);
    assert(pulse(&logic, 1400).beat);
}

static void test_alerts_once_after_three_filtered_values_above_150(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);
    uint32_t now_ms = 1000;
    (void)pulse(&logic, now_ms);

    for (int index = 0; index < 5; ++index) {
        now_ms += 380;
        ecg_result_t result = pulse(&logic, now_ms);
        assert(result.high_bpm_alert == (index == 4));
    }
    assert(!pulse(&logic, now_ms + 380).high_bpm_alert);
}

static void test_three_recovery_values_rearm_one_future_alert(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);
    uint32_t now_ms = 1000;
    (void)pulse(&logic, now_ms);

    bool first_alert = false;
    for (int index = 0; index < 5; ++index) {
        now_ms += 380;
        first_alert = first_alert || pulse(&logic, now_ms).high_bpm_alert;
    }
    assert(first_alert);

    for (int index = 0; index < 5; ++index) {
        now_ms += 500;
        assert(!pulse(&logic, now_ms).high_bpm_alert);
    }

    bool second_alert = false;
    for (int index = 0; index < 5; ++index) {
        now_ms += 380;
        second_alert = second_alert || pulse(&logic, now_ms).high_bpm_alert;
    }
    assert(second_alert);
}

static void test_neutral_bpm_breaks_consecutive_confirmation(void)
{
    ecg_logic_t logic = {
        .last_beat_ms = 1000,
        .rr_ms = {420, 420, 420, 420, 420},
        .rr_count = 5,
        .high_count = 2,
        .have_last_beat = true,
    };

    ecg_result_t neutral = pulse(&logic, 1420);
    assert(neutral.bpm > 140.0f && neutral.bpm < 150.0f);
    assert(logic.high_count == 0);
    assert(logic.recovery_count == 0);
    assert(!logic.alert_latched);
}

static void test_rail_samples_cannot_create_beats(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);

    assert(!ecg_logic_update(&logic, 0, false, 1000).beat);
    assert(!ecg_logic_update(&logic, 4095, false, 1400).beat);
    assert_close(logic.bpm, 0.0f);
}

static void test_lead_off_resets_history_and_alarm_state(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);
    (void)pulse(&logic, 1000);
    (void)pulse(&logic, 1380);
    (void)pulse(&logic, 1760);
    (void)pulse(&logic, 2140);

    ecg_result_t disconnected = ecg_logic_update(&logic, 3000, true, 2200);
    assert(!disconnected.leads_connected);
    assert(!disconnected.beat);
    assert(!disconnected.high_bpm_alert);
    assert_close(disconnected.bpm, 0.0f);

    ecg_result_t reconnected = pulse(&logic, 3000);
    assert(reconnected.leads_connected);
    assert(reconnected.beat);
    assert_close(reconnected.bpm, 0.0f);
    assert(!reconnected.high_bpm_alert);
}

int main(void)
{
    test_requires_three_rr_intervals_before_publishing_bpm();
    test_median_rejects_one_short_interval_spike();
    test_interval_below_minimum_is_not_a_beat();
    test_alerts_once_after_three_filtered_values_above_150();
    test_three_recovery_values_rearm_one_future_alert();
    test_neutral_bpm_breaks_consecutive_confirmation();
    test_rail_samples_cannot_create_beats();
    test_lead_off_resets_history_and_alarm_state();
    puts("test_ecg_logic: PASS");
    return 0;
}
