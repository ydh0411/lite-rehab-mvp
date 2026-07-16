#ifndef LITE_REHAB_SERIAL_TELEMETRY_H
#define LITE_REHAB_SERIAL_TELEMETRY_H

#include "ecg_monitor.h"
#include "motion_packet.h"

void serial_telemetry_header(void);
void serial_telemetry_packet(const motion_packet_t *packet);
void serial_telemetry_ecg(const ecg_monitor_sample_t *sample);

#endif
