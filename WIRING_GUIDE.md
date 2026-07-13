# Complete wiring guide / 完整接线指南

## 1. MYOSA wearable / MYOSA 佩戴端

Disconnect USB power before connecting JST cables. / 接 JST 线前先断开 USB 供电。

### JST cascade / JST 级联

```text
MYOSA motherboard I2C port
        │  four-wire JST cable
        ▼
MPU6050 board I2C port
        │  second four-wire JST cable
        ▼
SSD1306 OLED I2C port
```

1. Connect one MYOSA motherboard I²C socket to any equivalent MPU6050 socket.
2. Connect another MPU6050 socket to any OLED socket.
3. Follow the keyed connector direction. Do not reverse or force a JST plug.
4. Leave BMP180 and APDS9960 disconnected.
5. Connect the MYOSA USB-C port to the laptop or a USB power bank.

The four JST wires carry 3.3 V, GND, SDA, and SCL. Firmware uses GPIO21 for SDA and GPIO22 for SCL. Do not add separate jumper wires to these signals. / JST 四线包含 3.3 V、GND、SDA 和 SCL。固件使用 GPIO21/22，不需要再接杜邦线。

### MPU6050 orientation / MPU6050 安装方向

- Fix the sensor on the dorsal forearm, not on a loose cable.
- Point the printed X axis toward the hand.
- Point the Z axis away from the skin.
- Keep this orientation unchanged during data collection and demonstration.

将传感器固定在前臂背侧，X 轴指向手部，Z 轴朝外。不要让传感器悬挂在线上。

## 2. ESP32-S3 receiver / ESP32-S3 接收端

### External LED / 外接 LED

```text
ESP32-S3 GPIO2 ── 220–330 Ω ── LED long leg (+)
ESP32-S3 GND  ───────────────── LED short leg (-)
```

The resistor is mandatory. / 限流电阻必须使用。

### Supplied small passive buzzer / 套件小型无源蜂鸣器

For a small piezo buzzer drawing no more than 10 mA:

```text
ESP32-S3 GPIO18 ── 100–330 Ω ── buzzer (+)
ESP32-S3 GND    ───────────────── buzzer (-)
```

If the buzzer current is unknown, use the optional transistor circuit:

```text
GPIO18 ── 1 kΩ ── NPN base
GND    ────────── NPN emitter
3V3    ── buzzer (+)
buzzer (-) ────── NPN collector
```

Never connect 5 V to GPIO18. / 不要将 5 V 接入 GPIO18。

### USB connection / USB 连接

Use the ESP32-S3 native USB port labelled **USB**, not the USB-to-UART port, because the receiver firmware uses USB Serial/JTAG. GPIO19 and GPIO20 must remain unused.

接收端固件使用原生 USB Serial/JTAG，应连接标有 **USB** 的接口，不要占用 GPIO19/20。

## 3. Power arrangement / 供电方式

- During development, power each board from a separate laptop USB port.
- For the demonstration, the MYOSA wearable may use a small USB power bank.
- Keep the ESP32-S3 connected to the laptop for serial data.
- The two boards communicate wirelessly by BLE, so their grounds do not need to be connected.

## 4. MaixCAM 2 camera / MaixCAM 2 相机

No GPIO or breadboard wires are required. / 不需要连接 GPIO 或面包板。

```text
MaixCAM 2 Type-C data port ── Type-C data cable ── laptop USB
ESP32-S3 native USB port   ── separate USB cable ─ laptop USB
MYOSA wearable             ── BLE ──────────────── ESP32-S3
```

1. Use a Type-C **data** cable, not a charge-only cable.
2. Enable the MaixCAM 2 USB NCM/network function if the system image requires USB-function selection.
3. Run `maixcam2/main.py` through MaixVision with its committed `MODE = "rtsp"` and use the RTSP URL printed in the terminal.
4. Keep MaixCAM 2 1.5–2.0 m away at chest height, in landscape orientation.
5. For the right-arm demo, keep the right shoulder, elbow, wrist, and hip in frame.

MaixCAM 2 only supplies video. It has no electrical connection to the wearable
or receiver. RTSP over USB NCM is the primary path; optional UVC instructions are
in [`maixcam2/README.md`](maixcam2/README.md). / MaixCAM 2 只提供视频，与穿戴端和接收端没有电气连接；默认使用 USB NCM 上的 RTSP，可选 UVC 说明见相机文档。

## 5. Pre-power checklist / 上电前检查

- JST plugs follow the keyed direction.
- LED has a series resistor and correct polarity.
- Buzzer polarity is correct.
- No 5 V wire reaches any GPIO.
- MPU6050 is fixed firmly.
- BMP180 and APDS9960 are disconnected.
- MaixCAM 2 and ESP32-S3 use separate data-capable USB connections.

## 6. Expected behavior / 预期现象

1. MYOSA OLED shows `KEEP STILL` for the two-second calibration.
2. OLED then shows exercise, repetition count, quality, and BLE state.
3. ESP32-S3 LED blinks while scanning and stays on after connection.
4. A valid repetition produces one high beep.
5. A fast or short-range movement produces two low warning tones.
