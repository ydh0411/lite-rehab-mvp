#include "receiver_display.h"

#include <stdio.h>
#include <string.h>

#include "driver/i2c_master.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "ssd1306.h"

#define DISPLAY_SDA_GPIO 8
#define DISPLAY_SCL_GPIO 9

typedef struct {
    bool connected;
    bool leads_connected;
    float bpm;
    uint16_t rep_count;
    uint8_t state;
    uint8_t quality;
} display_state_t;

static const char *TAG = "receiver_display";
static i2c_master_bus_handle_t display_bus;
static ssd1306_t display;
static SemaphoreHandle_t state_mutex;
static display_state_t current_state;

static const char *motion_name(uint8_t state)
{
    if (state == MOTION_STATE_FOREARM_ROTATION) return "ROTATE";
    if (state == MOTION_STATE_ELBOW_FLEXION) return "ELBOW";
    return "IDLE";
}

static const char *quality_name(uint8_t quality)
{
    if (quality == MOTION_QUALITY_OK) return "OK";
    if (quality == MOTION_QUALITY_TOO_FAST) return "FAST";
    if (quality == MOTION_QUALITY_INSUFFICIENT_RANGE) return "RANGE";
    return "WAIT";
}

static void display_task(void *arg)
{
    (void)arg;
    while (true) {
        display_state_t snapshot;
        xSemaphoreTake(state_mutex, portMAX_DELAY);
        snapshot = current_state;
        xSemaphoreGive(state_mutex);

        char bpm_line[22];
        char reps_line[22];
        if (snapshot.leads_connected) {
            snprintf(bpm_line, sizeof(bpm_line), "ECG BPM %03.0f", snapshot.bpm);
        } else {
            snprintf(bpm_line, sizeof(bpm_line), "ECG LEADS OFF");
        }
        snprintf(reps_line, sizeof(reps_line), "REPS %03u", snapshot.rep_count);

        ssd1306_clear(&display);
        ssd1306_text(&display, 0, "LITEREHAB");
        ssd1306_text(&display, 1, snapshot.connected ? "BLE OK" : "BLE WAIT");
        ssd1306_text(&display, 3, bpm_line);
        ssd1306_text(&display, 5, motion_name(snapshot.state));
        ssd1306_text(&display, 6, reps_line);
        ssd1306_text(&display, 7, quality_name(snapshot.quality));
        esp_err_t error = ssd1306_flush(&display);
        if (error != ESP_OK) {
            ESP_LOGW(TAG, "OLED update failed: %s", esp_err_to_name(error));
            display.available = false;
            vTaskDelete(NULL);
        }
        vTaskDelay(pdMS_TO_TICKS(200));
    }
}

esp_err_t receiver_display_init(void)
{
    memset(&current_state, 0, sizeof(current_state));
    state_mutex = xSemaphoreCreateMutex();
    if (state_mutex == NULL) return ESP_ERR_NO_MEM;

    const i2c_master_bus_config_t bus_config = {
        .i2c_port = I2C_NUM_0,
        .sda_io_num = DISPLAY_SDA_GPIO,
        .scl_io_num = DISPLAY_SCL_GPIO,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    esp_err_t error = i2c_new_master_bus(&bus_config, &display_bus);
    if (error != ESP_OK) return error;

    error = ssd1306_init(&display, display_bus);
    if (error != ESP_OK) return error;

    if (xTaskCreate(display_task, "receiver_display", 3072, NULL, 3, NULL)
        != pdPASS) {
        display.available = false;
        return ESP_ERR_NO_MEM;
    }
    ESP_LOGI(TAG, "SSD1306 ready on GPIO8/GPIO9");
    return ESP_OK;
}

void receiver_display_set_connected(bool connected)
{
    if (state_mutex == NULL) return;
    xSemaphoreTake(state_mutex, portMAX_DELAY);
    current_state.connected = connected;
    xSemaphoreGive(state_mutex);
}

void receiver_display_set_motion(const motion_packet_t *packet)
{
    if (state_mutex == NULL || packet == NULL) return;
    xSemaphoreTake(state_mutex, portMAX_DELAY);
    current_state.rep_count = packet->rep_count;
    current_state.state = packet->state;
    current_state.quality = packet->quality;
    xSemaphoreGive(state_mutex);
}

void receiver_display_set_ecg(const ecg_monitor_sample_t *sample)
{
    if (state_mutex == NULL || sample == NULL) return;
    xSemaphoreTake(state_mutex, portMAX_DELAY);
    current_state.leads_connected = sample->result.leads_connected;
    current_state.bpm = sample->result.bpm;
    xSemaphoreGive(state_mutex);
}
