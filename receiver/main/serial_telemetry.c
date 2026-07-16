#include "serial_telemetry.h"

#include <stdio.h>

static const char *state_name(uint8_t state)
{
    if (state == MOTION_STATE_FOREARM_ROTATION) return "forearm_rotation";
    if (state == MOTION_STATE_ELBOW_FLEXION) return "elbow_flexion";
    return "idle";
}

static const char *quality_name(uint8_t quality)
{
    if (quality == MOTION_QUALITY_OK) return "ok";
    if (quality == MOTION_QUALITY_TOO_FAST) return "too_fast";
    if (quality == MOTION_QUALITY_INSUFFICIENT_RANGE) return "insufficient_range";
    return "none";
}

void serial_telemetry_header(void)
{
    puts("# LiteRehab receiver ready");
    puts("# IMU,t_ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,state,rep_count,quality");
    puts("# ECG,t_ms,raw_adc,bpm,leads_connected,beat,rapid_change");
}

void serial_telemetry_packet(const motion_packet_t *packet)
{
    if (packet == NULL) return;
    printf("IMU,%lu,%.5f,%.5f,%.5f,%.3f,%.3f,%.3f,%s,%u,%s\n",
           (unsigned long)packet->timestamp_ms,
           packet->accel[0] / 16384.0f, packet->accel[1] / 16384.0f,
           packet->accel[2] / 16384.0f, packet->gyro[0] / 131.0f,
           packet->gyro[1] / 131.0f, packet->gyro[2] / 131.0f,
           state_name(packet->state), packet->rep_count,
           quality_name(packet->quality));
    fflush(stdout);
}

void serial_telemetry_ecg(const ecg_monitor_sample_t *sample)
{
    if (sample == NULL) return;
    printf("ECG,%lu,%d,%.2f,%u,%u,%u\n",
           (unsigned long)sample->timestamp_ms,
           sample->raw_adc,
           sample->result.bpm,
           sample->result.leads_connected ? 1u : 0u,
           sample->result.beat ? 1u : 0u,
           sample->result.rapid_change ? 1u : 0u);
    fflush(stdout);
}
