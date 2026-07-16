idf_component_register(
    SRCS "app_main.c" "ble_client.c" "ecg_monitor.c" "receiver_display.c"
         "receiver_outputs.c" "serial_telemetry.c" "../../shared/ecg_logic.c"
         "../../shared/ecg_lead_filter.c" "../../shared/ecg_alert_gate.c"
         "../../shared/motion_packet.c" "../../shared/feedback_logic.c"
         "../../wearable/main/ssd1306.c"
    INCLUDE_DIRS "." "../../shared" "../../wearable/main"
    PRIV_REQUIRES bt nvs_flash esp_adc esp_driver_gpio esp_driver_i2c
                  esp_driver_ledc
)
