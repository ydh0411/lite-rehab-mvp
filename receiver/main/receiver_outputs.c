#include "receiver_outputs.h"

#include "driver/gpio.h"
#include "driver/ledc.h"
#include "ecg_alert_gate.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#define LED_GPIO GPIO_NUM_2
#define BUZZER_GPIO GPIO_NUM_18

static QueueHandle_t feedback_queue;
static bool is_connected;
static ecg_alert_gate_t ecg_alert_gate;

typedef enum {
    OUTPUT_EVENT_MOTION_SUCCESS,
    OUTPUT_EVENT_MOTION_WARNING,
    OUTPUT_EVENT_ECG_RAPID,
} output_event_t;

static void tone(unsigned frequency, unsigned duration_ms)
{
    ledc_set_freq(LEDC_LOW_SPEED_MODE, LEDC_TIMER_0, frequency);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 512);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
    vTaskDelay(pdMS_TO_TICKS(duration_ms));
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
}

static void feedback_task(void *arg)
{
    (void)arg;
    output_event_t event;
    while (true) {
        if (xQueueReceive(feedback_queue, &event, pdMS_TO_TICKS(500)) == pdTRUE) {
            if (event == OUTPUT_EVENT_MOTION_WARNING) {
                tone(280, 180); vTaskDelay(pdMS_TO_TICKS(80)); tone(220, 220);
            } else if (event == OUTPUT_EVENT_MOTION_SUCCESS) {
                tone(880, 100);
            } else if (event == OUTPUT_EVENT_ECG_RAPID) {
                for (int i = 0; i < 5; ++i) {
                    tone(1000, 50);
                    vTaskDelay(pdMS_TO_TICKS(50));
                }
                ecg_alert_gate_release(&ecg_alert_gate);
            }
        } else if (!is_connected) {
            gpio_set_level(LED_GPIO, !gpio_get_level(LED_GPIO));
        } else {
            gpio_set_level(LED_GPIO, 1);
        }
    }
}

esp_err_t receiver_outputs_init(void)
{
    const gpio_config_t led = {
        .pin_bit_mask = 1ULL << LED_GPIO,
        .mode = GPIO_MODE_INPUT_OUTPUT,
    };
    ESP_ERROR_CHECK(gpio_config(&led));
    const ledc_timer_config_t timer = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = LEDC_TIMER_10_BIT,
        .timer_num = LEDC_TIMER_0,
        .freq_hz = 1000,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ESP_ERROR_CHECK(ledc_timer_config(&timer));
    const ledc_channel_config_t channel = {
        .gpio_num = BUZZER_GPIO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LEDC_CHANNEL_0,
        .timer_sel = LEDC_TIMER_0,
        .duty = 0,
    };
    ESP_ERROR_CHECK(ledc_channel_config(&channel));
    feedback_queue = xQueueCreate(8, sizeof(output_event_t));
    if (feedback_queue == NULL) return ESP_ERR_NO_MEM;
    ecg_alert_gate_init(&ecg_alert_gate);
    xTaskCreate(feedback_task, "feedback", 3072, NULL, 4, NULL);
    return ESP_OK;
}

void receiver_outputs_set_connected(bool connected)
{
    is_connected = connected;
    gpio_set_level(LED_GPIO, connected ? 1 : 0);
}

void receiver_outputs_feedback(feedback_event_t event)
{
    if (feedback_queue == NULL || event == FEEDBACK_EVENT_NONE) return;
    const output_event_t output =
        event == FEEDBACK_EVENT_WARNING
            ? OUTPUT_EVENT_MOTION_WARNING
            : OUTPUT_EVENT_MOTION_SUCCESS;
    (void)xQueueSend(feedback_queue, &output, 0);
}

void receiver_outputs_ecg_alert(void)
{
    if (feedback_queue == NULL) return;
    if (!ecg_alert_gate_try_acquire(&ecg_alert_gate)) return;
    const output_event_t output = OUTPUT_EVENT_ECG_RAPID;
    if (xQueueSend(feedback_queue, &output, 0) != pdTRUE) {
        ecg_alert_gate_release(&ecg_alert_gate);
    }
}
