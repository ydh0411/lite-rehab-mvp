#ifndef LITE_REHAB_RECEIVER_DISPLAY_H
#define LITE_REHAB_RECEIVER_DISPLAY_H

#include <stdbool.h>

#include "ecg_monitor.h"
#include "esp_err.h"
#include "motion_packet.h"

esp_err_t receiver_display_init(void);
void receiver_display_set_connected(bool connected);
void receiver_display_set_motion(const motion_packet_t *packet);
void receiver_display_set_ecg(const ecg_monitor_sample_t *sample);

#endif
