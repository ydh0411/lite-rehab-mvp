#include "motion_logic.h"

#include <math.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846f
#endif

motion_config_t motion_default_config(void)
{
    return (motion_config_t){
        .filter_alpha = 0.25f,
        .comp_alpha = 0.98f,
        .enter_threshold_dps = 45.0f,
        .exit_threshold_dps = 15.0f,
        .dominance_ratio = 1.30f,
        .min_range_deg = 35.0f,
        .too_fast_peak_dps = 280.0f,
        .min_rep_duration_ms = 450,
        .max_rep_duration_ms = 5000,
        .refractory_ms = 300,
        .adapt_k = 0.8f,
        .adapt_floor_dps = 25.0f,
        .adapt_ceil_dps = 150.0f,
    };
}

void motion_logic_init(motion_logic_t *logic, const motion_config_t *config)
{
    if (logic == NULL) return;
    memset(logic, 0, sizeof(*logic));
    logic->config = config != NULL ? *config : motion_default_config();
    logic->result.state = MOTION_STATE_IDLE;
    logic->result.last_completed_state = MOTION_STATE_IDLE;
    logic->result.quality = MOTION_QUALITY_NONE;
    logic->adaptive_enter = logic->config.enter_threshold_dps;
    logic->adaptive_exit = logic->config.exit_threshold_dps;
}

static void update_complementary_filter(motion_logic_t *logic,
                                         float gx, float gy,
                                         float ax, float ay, float az,
                                         float dt_s)
{
    float roll_acc = atan2f(ay, az) * 180.0f / M_PI;
    float pitch_acc = atan2f(-ax, sqrtf(ay * ay + az * az)) * 180.0f / M_PI;

    if (!logic->cf_initialized) {
        logic->roll_deg = roll_acc;
        logic->pitch_deg = pitch_acc;
        logic->cf_initialized = true;
    } else {
        float alpha = logic->config.comp_alpha;
        logic->roll_deg = alpha * (logic->roll_deg + gx * dt_s)
                        + (1.0f - alpha) * roll_acc;
        logic->pitch_deg = alpha * (logic->pitch_deg + gy * dt_s)
                         + (1.0f - alpha) * pitch_acc;
    }
}

static void update_adaptive_thresholds(motion_logic_t *logic, float signal_mag)
{
    logic->signal_rms_sq = 0.95f * logic->signal_rms_sq
                         + 0.05f * signal_mag * signal_mag;
    float rms = sqrtf(logic->signal_rms_sq);
    logic->adaptive_enter = logic->config.enter_threshold_dps
                          + logic->config.adapt_k * rms;
    if (logic->adaptive_enter > logic->config.adapt_ceil_dps)
        logic->adaptive_enter = logic->config.adapt_ceil_dps;
    if (logic->adaptive_enter < logic->config.adapt_floor_dps)
        logic->adaptive_enter = logic->config.adapt_floor_dps;
    logic->adaptive_exit = logic->adaptive_enter * 0.33f;
}

static motion_state_t classify_axis(const motion_logic_t *logic,
                                     float gx, float gy,
                                     float ax, float ay)
{
    float ax_abs = fabsf(gx);
    float ay_abs = fabsf(gy);
    if (ax_abs < logic->adaptive_enter && ay_abs < logic->adaptive_enter)
        return MOTION_STATE_IDLE;

    float gyro_score = ax_abs / (ay_abs + 1e-6f);
    float accel_x = fabsf(ax);
    float accel_y = fabsf(ay);
    float accel_score = accel_x / (accel_y + 1e-6f);

    if (gyro_score >= logic->config.dominance_ratio) {
        if (accel_score >= 0.4f) return MOTION_STATE_FOREARM_ROTATION;
        if (gyro_score >= 2.5f) return MOTION_STATE_FOREARM_ROTATION;
    }
    if (1.0f / gyro_score >= logic->config.dominance_ratio) {
        if (1.0f / accel_score >= 0.4f) return MOTION_STATE_ELBOW_FLEXION;
        if (1.0f / gyro_score >= 2.5f) return MOTION_STATE_ELBOW_FLEXION;
    }
    return logic->active_state;
}

static float axis_value(motion_state_t state, float gx, float gy)
{
    return state == MOTION_STATE_ELBOW_FLEXION ? gy : gx;
}

static void finish_repetition(motion_logic_t *logic, uint32_t timestamp_ms)
{
    const uint32_t duration = timestamp_ms - logic->start_ms;
    logic->result.rep_completed = true;
    logic->result.last_completed_state = logic->active_state;
    if (logic->integrated_abs_deg < logic->config.min_range_deg) {
        logic->result.quality = MOTION_QUALITY_INSUFFICIENT_RANGE;
    } else {
        logic->result.rep_count++;
        logic->result.quality =
            (duration < logic->config.min_rep_duration_ms ||
             logic->peak_dps > logic->config.too_fast_peak_dps)
                ? MOTION_QUALITY_TOO_FAST
                : MOTION_QUALITY_OK;
    }
    logic->last_completed_ms = timestamp_ms;
    logic->phase = 0;
    logic->active_state = MOTION_STATE_IDLE;
    logic->integrated_abs_deg = 0.0f;
    logic->peak_dps = 0.0f;
}

motion_result_t motion_logic_update(motion_logic_t *logic,
                                    float gx_dps, float gy_dps, float gz_dps,
                                    float ax_g, float ay_g, float az_g,
                                    uint32_t timestamp_ms)
{
    if (logic == NULL) return (motion_result_t){0};
    logic->result.rep_completed = false;

    const float input[3] = {gx_dps, gy_dps, gz_dps};
    for (int i = 0; i < 3; ++i) {
        logic->result.filtered_gyro[i] +=
            logic->config.filter_alpha *
            (input[i] - logic->result.filtered_gyro[i]);
    }

    uint32_t dt_ms = logic->initialized ? timestamp_ms - logic->previous_ms : 0;
    if (dt_ms > 100) dt_ms = 100;
    logic->initialized = true;
    logic->previous_ms = timestamp_ms;

    const float gx = logic->result.filtered_gyro[0];
    const float gy = logic->result.filtered_gyro[1];
    if (dt_ms > 0) {
        update_complementary_filter(logic, gx, gy, ax_g, ay_g, az_g,
                                     dt_ms / 1000.0f);
    }
    logic->result.roll_deg = logic->roll_deg;
    logic->result.pitch_deg = logic->pitch_deg;

    const float signal_mag = fmaxf(fabsf(gx), fabsf(gy));
    if (logic->phase == 0 && signal_mag < logic->config.enter_threshold_dps) {
        update_adaptive_thresholds(logic, signal_mag);
    }

    const motion_state_t classified = classify_axis(logic, gx, gy, ax_g, ay_g);

    if (logic->phase == 0) {
        logic->result.state = classified;
        if (classified != MOTION_STATE_IDLE &&
            timestamp_ms - logic->last_completed_ms >= logic->config.refractory_ms) {
            const float value = axis_value(classified, gx, gy);
            logic->active_state = classified;
            logic->start_sign = value >= 0.0f ? 1 : -1;
            logic->start_ms = timestamp_ms;
            logic->integrated_abs_deg = 0.0f;
            logic->peak_dps = fabsf(value);
            logic->phase = 1;
        }
        return logic->result;
    }

    logic->result.state = logic->active_state;
    const float value = axis_value(logic->active_state, gx, gy);
    logic->integrated_abs_deg += fabsf(value) * ((float)dt_ms / 1000.0f);
    if (fabsf(value) > logic->peak_dps) logic->peak_dps = fabsf(value);

    if (logic->phase == 1 &&
        value * (float)logic->start_sign <= -logic->adaptive_enter) {
        logic->phase = 2;
    }

    if (logic->phase == 2 && fabsf(value) <= logic->adaptive_exit) {
        finish_repetition(logic, timestamp_ms);
        logic->result.state = MOTION_STATE_IDLE;
    } else if (timestamp_ms - logic->start_ms > logic->config.max_rep_duration_ms) {
        logic->result.quality = MOTION_QUALITY_INSUFFICIENT_RANGE;
        logic->phase = 0;
        logic->active_state = MOTION_STATE_IDLE;
        logic->result.state = MOTION_STATE_IDLE;
    }

    return logic->result;
}
