#include <stdio.h>

#include "ble_client.h"
#include "ecg_monitor.h"
#include "esp_log.h"
#include "feedback_logic.h"
#include "receiver_display.h"
#include "receiver_outputs.h"
#include "serial_telemetry.h"

static const char *TAG = "receiver";
static uint16_t previous_sequence;
static bool have_sequence;
static feedback_logic_t feedback_logic;

static void ecg_received(const ecg_monitor_sample_t *sample)
{
    serial_telemetry_ecg(sample);
    receiver_display_set_ecg(sample);
    if (sample->result.rapid_change) {
        receiver_outputs_ecg_alert();
    }
}

static void connection_changed(bool connected)
{
    receiver_outputs_set_connected(connected);
    receiver_display_set_connected(connected);
    printf("# BLE %s\n", connected ? "connected" : "disconnected");
    fflush(stdout);
    if (!connected) have_sequence = false;
}

static void packet_received(const motion_packet_t *packet)
{
    if (have_sequence && (uint16_t)(previous_sequence + 1) != packet->sequence) {
        printf("# packet_gap expected=%u received=%u\n",
               (uint16_t)(previous_sequence + 1), packet->sequence);
    }
    previous_sequence = packet->sequence;
    have_sequence = true;
    receiver_outputs_feedback(feedback_logic_update(&feedback_logic, packet));
    receiver_display_set_motion(packet);
    serial_telemetry_packet(packet);
}

void app_main(void)
{
    ESP_ERROR_CHECK(receiver_outputs_init());
    esp_err_t display_error = receiver_display_init();
    if (display_error != ESP_OK) {
        ESP_LOGW(TAG, "OLED unavailable: %s", esp_err_to_name(display_error));
    }
    feedback_logic_init(&feedback_logic);
    serial_telemetry_header();
    esp_err_t ecg_error = ecg_monitor_init(ecg_received);
    if (ecg_error != ESP_OK) {
        ESP_LOGW(TAG, "ECG unavailable: %s", esp_err_to_name(ecg_error));
    }
    ESP_LOGI(TAG, "starting BLE receiver");
    ESP_ERROR_CHECK(ble_client_init(packet_received, connection_changed));
}
