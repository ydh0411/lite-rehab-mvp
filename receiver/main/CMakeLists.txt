idf_component_register(
    SRCS "app_main.c" "ble_client.c" "receiver_outputs.c" "serial_telemetry.c"
         "../../shared/motion_packet.c" "../../shared/feedback_logic.c"
    INCLUDE_DIRS "." "../../shared"
    PRIV_REQUIRES bt nvs_flash esp_driver_gpio esp_driver_ledc
)
