#include <assert.h>
#include <math.h>
#include <stdio.h>

#include "motion_logic.h"

static motion_result_t feed_axis_cycle(motion_logic_t *logic,
                                       float gx,
                                       float gy,
                                       int samples_each_way,
                                       uint32_t *time_ms)
{
    motion_result_t result = {0};
    for (int i = 0; i < samples_each_way; ++i) {
        *time_ms += 20;
        result = motion_logic_update(logic, gx, gy, 0.0f,
                                     0.0f, 0.0f, 1.0f, *time_ms);
    }
    for (int i = 0; i < samples_each_way; ++i) {
        *time_ms += 20;
        result = motion_logic_update(logic, -gx, -gy, 0.0f,
                                     0.0f, 0.0f, 1.0f, *time_ms);
    }
    for (int i = 0; i < 5; ++i) {
        *time_ms += 20;
        result = motion_logic_update(logic, 0.0f, 0.0f, 0.0f,
                                     0.0f, 0.0f, 1.0f, *time_ms);
    }
    return result;
}

int main(void)
{
    motion_config_t config = motion_default_config();
    config.filter_alpha = 1.0f;
    config.enter_threshold_dps = 30.0f;
    config.exit_threshold_dps = 12.0f;
    config.dominance_ratio = 1.25f;
    config.min_range_deg = 30.0f;
    config.min_rep_duration_ms = 300;
    config.max_rep_duration_ms = 3000;
    config.too_fast_peak_dps = 250.0f;
    config.refractory_ms = 100;

    motion_logic_t logic;
    motion_logic_init(&logic, &config);
    uint32_t now = 0;

    for (int i = 0; i < 20; ++i) {
        now += 20;
        motion_result_t idle = motion_logic_update(
            &logic, 2.0f, -1.0f, 0.5f, 0.0f, 0.0f, 1.0f, now);
        assert(idle.state == MOTION_STATE_IDLE);
        assert(idle.rep_count == 0);
    }

    motion_result_t rotation = feed_axis_cycle(&logic, 100.0f, 0.0f, 10, &now);
    assert(rotation.rep_count == 1);
    assert(rotation.last_completed_state == MOTION_STATE_FOREARM_ROTATION);
    assert(rotation.quality == MOTION_QUALITY_OK);

    now += 200;
    motion_result_t elbow = feed_axis_cycle(&logic, 0.0f, 100.0f, 10, &now);
    assert(elbow.rep_count == 2);
    assert(elbow.last_completed_state == MOTION_STATE_ELBOW_FLEXION);

    motion_logic_init(&logic, &config);
    now = 0;
    motion_result_t fast = feed_axis_cycle(&logic, 350.0f, 0.0f, 8, &now);
    assert(fast.rep_count == 1);
    assert(fast.quality == MOTION_QUALITY_TOO_FAST);

    motion_logic_init(&logic, &config);
    now = 0;
    motion_result_t short_range = feed_axis_cycle(&logic, 40.0f, 0.0f, 5, &now);
    assert(short_range.rep_count == 0);
    assert(short_range.quality == MOTION_QUALITY_INSUFFICIENT_RANGE);

    motion_logic_init(&logic, &config);
    now = 0;
    for (int i = 0; i < 20; ++i) {
        now += 20;
        (void)motion_logic_update(&logic, 2.0f, 1.0f, 0.0f,
                                  0.0f, 0.0f, 1.0f, now);
    }
    const float idle_threshold = logic.adaptive_enter;
    now += 20;
    (void)motion_logic_update(&logic, 300.0f, 0.0f, 0.0f,
                              1.0f, 0.0f, 0.0f, now);
    assert(logic.adaptive_enter == idle_threshold);

    puts("test_motion_logic: PASS");
    return 0;
}
