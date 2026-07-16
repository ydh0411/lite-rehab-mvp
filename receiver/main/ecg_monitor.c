#include "ecg_monitor.h"

#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define ECG_ADC_CHANNEL ADC_CHANNEL_3
#define ECG_LO_PLUS_GPIO GPIO_NUM_5
#define ECG_LO_MINUS_GPIO GPIO_NUM_6
#define ECG_SAMPLE_PERIOD_MS 10

static const char *TAG = "ecg_monitor";
static adc_oneshot_unit_handle_t adc_handle;
static ecg_monitor_callback_t on_sample;

static void ecg_task(void *arg)
{
    (void)arg;
    ecg_logic_t logic;
    ecg_logic_init(&logic);
    TickType_t last_wake = xTaskGetTickCount();

    while (true) {
        const bool leads_off =
            gpio_get_level(ECG_LO_PLUS_GPIO) != 0 ||
            gpio_get_level(ECG_LO_MINUS_GPIO) != 0;
        int raw_adc = 0;
        esp_err_t error = ESP_OK;
        if (!leads_off) {
            error = adc_oneshot_read(adc_handle, ECG_ADC_CHANNEL, &raw_adc);
        }
        if (error == ESP_OK) {
            const uint32_t now_ms = (uint32_t)(esp_timer_get_time() / 1000);
            const ecg_monitor_sample_t sample = {
                .timestamp_ms = now_ms,
                .raw_adc = raw_adc,
                .result = ecg_logic_update(&logic, raw_adc, leads_off, now_ms),
            };
            on_sample(&sample);
        } else {
            ESP_LOGW(TAG, "ADC read failed: %s", esp_err_to_name(error));
        }
        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(ECG_SAMPLE_PERIOD_MS));
    }
}

esp_err_t ecg_monitor_init(ecg_monitor_callback_t callback)
{
    if (callback == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    const gpio_config_t lead_inputs = {
        .pin_bit_mask =
            (1ULL << ECG_LO_PLUS_GPIO) | (1ULL << ECG_LO_MINUS_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
    };
    esp_err_t error = gpio_config(&lead_inputs);
    if (error != ESP_OK) {
        return error;
    }

    const adc_oneshot_unit_init_cfg_t unit_config = {
        .unit_id = ADC_UNIT_1,
    };
    error = adc_oneshot_new_unit(&unit_config, &adc_handle);
    if (error != ESP_OK) {
        return error;
    }

    const adc_oneshot_chan_cfg_t channel_config = {
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    error = adc_oneshot_config_channel(
        adc_handle, ECG_ADC_CHANNEL, &channel_config);
    if (error != ESP_OK) {
        adc_oneshot_del_unit(adc_handle);
        adc_handle = NULL;
        return error;
    }

    on_sample = callback;
    if (xTaskCreate(ecg_task, "ecg", 3072, NULL, 5, NULL) != pdPASS) {
        on_sample = NULL;
        adc_oneshot_del_unit(adc_handle);
        adc_handle = NULL;
        return ESP_ERR_NO_MEM;
    }
    ESP_LOGI(TAG, "CJMCU-8232 sampling GPIO4 at 100 Hz");
    return ESP_OK;
}
