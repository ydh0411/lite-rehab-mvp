# Complete wiring guide / 完整接线指南

## 1. MYOSA wearable / MYOSA 佩戴端

Disconnect USB power before connecting JST cables. / 接 JST 线前先断开 USB 供电。

### Lightweight wearable connection / 轻量穿戴连接

```text
MYOSA motherboard I2C port
        │  one short four-wire JST cable
        ▼
MPU6050 board I2C port
```

1. Connect one MYOSA motherboard I²C socket to an equivalent MPU6050 socket.
2. Do not place the OLED after the MPU6050 in the demo wiring; it moves to the receiver.
3. Fix the MYOSA board and MPU6050 to one rigid backing on the forearm.
4. Fold the short JST cable into a relaxed curve and tape it down so no loose tail can swing.
5. Follow the keyed connector direction. Do not reverse or force a JST plug.
6. Leave BMP180 and APDS9960 disconnected.
7. Connect the MYOSA USB-C port to the laptop or a USB power bank.

The four JST wires carry 3.3 V, GND, SDA, and SCL. Firmware uses GPIO21 for SDA and GPIO22 for SCL. Do not add separate jumper wires to these signals. / JST 四线包含 3.3 V、GND、SDA 和 SCL。固件使用 GPIO21/22，不需要再接杜邦线。

### MPU6050 orientation / MPU6050 安装方向

- Fix the sensor on the dorsal forearm, not on a loose cable.
- Point the printed X axis toward the hand.
- Point the Z axis away from the skin.
- Keep this orientation unchanged during data collection and demonstration.

将传感器固定在前臂背侧，X 轴指向手部，Z 轴朝外。不要让传感器悬挂在线上。

## 2. ESP32-S3 receiver hub / ESP32-S3 接收中心

### Complete pin allocation / 完整引脚分配

| Function / 功能 | ESP32-S3 | Peripheral / 外设 |
|---|---:|---|
| Connection LED / 连接灯 | GPIO2 | LED through 220–330 Ω / LED 串联 220–330 Ω |
| ECG analog / ECG 模拟信号 | GPIO4 (ADC1_CH3) | CJMCU-8232 `OUTPUT` |
| ECG lead-off + / 导联脱落 + | GPIO5 | CJMCU-8232 `LO+` |
| ECG lead-off − / 导联脱落 − | GPIO6 | CJMCU-8232 `LO-` |
| OLED data / OLED 数据 | GPIO8 | SSD1306 `SDA` |
| OLED clock / OLED 时钟 | GPIO9 | SSD1306 `SCL` |
| Passive buzzer / 无源蜂鸣器 | GPIO18 | Buzzer through 100–330 Ω / 蜂鸣器串联 100–330 Ω |
| Power / 电源 | 3V3 | OLED `VCC`, CJMCU `3.3V`, CJMCU `SDN` |
| Ground / 地 | GND | OLED and CJMCU `GND`, LED/buzzer return |

Keep GPIO19/20 free for native USB. Do not use GPIO35/36/37 on the N16R8 board; GPIO36 from the merged Arduino reference is not an ESP32-S3 ADC input and the octal-memory module reserves these pins. / GPIO19/20 留给原生 USB；N16R8 板不要使用 GPIO35/36/37。合并的 Arduino 参考代码中的 GPIO36 不是 ESP32-S3 ADC 输入，并且这些引脚由 Octal Memory 占用。

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

### Receiver OLED / 接收端 OLED

```text
ESP32-S3 3V3   ── OLED VCC
ESP32-S3 GND   ── OLED GND
ESP32-S3 GPIO8 ── OLED SDA
ESP32-S3 GPIO9 ── OLED SCL
```

If the MYOSA OLED only exposes keyed JST sockets, use a four-pin JST-to-Dupont adapter or breakout. Verify `3V3/GND/SDA/SCL` from the board labels or schematic; do not infer the order from wire color and do not cut a keyed cable for the demo. / 如果 MYOSA OLED 只有 JST 插座，请使用四针 JST 转杜邦线或转接板，并根据丝印/原理图确认 `3V3/GND/SDA/SCL`，不要只凭线色判断，也不要为演示剪线。

### CJMCU-8232 ECG / CJMCU-8232 心电模块

```text
ESP32-S3 3V3   ── CJMCU-8232 3.3V
ESP32-S3 GND   ── CJMCU-8232 GND
ESP32-S3 GPIO4 ── CJMCU-8232 OUTPUT
ESP32-S3 GPIO5 ── CJMCU-8232 LO+
ESP32-S3 GPIO6 ── CJMCU-8232 LO-
ESP32-S3 3V3   ── CJMCU-8232 SDN
```

Use 3.3 V only. `SDN` is tied high so the module remains enabled. Connect the supplied three-electrode cable through the 3.5 mm jack and follow the cable/module RA, LA, and RL labels rather than relying only on colors. Put the CJMCU board away from the buzzer and USB cable, keep the `OUTPUT` wire short, and do not bundle it with the GPIO18 buzzer wire. / 只能使用 3.3 V；`SDN` 拉高保持模块启用。通过 3.5 mm 接口连接三电极线，并按 RA/LA/RL 标签接电极，不要只看颜色。CJMCU 板应远离蜂鸣器和 USB 线，`OUTPUT` 线尽量短，不要与 GPIO18 蜂鸣器线捆扎。

### USB connection / USB 连接

Use the ESP32-S3 native USB port labelled **USB**, not the USB-to-UART port, because the receiver firmware uses USB Serial/JTAG. GPIO19 and GPIO20 must remain unused.

接收端固件使用原生 USB Serial/JTAG，应连接标有 **USB** 的接口，不要占用 GPIO19/20。

## 3. Power arrangement / 供电方式

- During development without attached ECG electrodes, power each board from a separate laptop USB port.
- For the demonstration, the MYOSA wearable may use a small USB power bank.
- Keep the ESP32-S3 connected to the laptop for serial data.
- The two boards communicate wirelessly by BLE, so their grounds do not need to be connected.
- While ECG electrodes touch a person, run the laptop from its battery and disconnect its mains charger. This classroom prototype is not medically isolated and is not a medical device.

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
- MYOSA and MPU6050 are rigidly mounted and the JST cable is restrained.
- LED has a series resistor and correct polarity.
- Buzzer polarity is correct.
- No 5 V wire reaches any GPIO.
- CJMCU-8232 `3.3V` and `SDN` go to 3V3, never 5V.
- CJMCU `OUTPUT/LO+/LO-` go to GPIO4/5/6.
- OLED `SDA/SCL` go to GPIO8/9 with verified power-pin order.
- ECG analog wiring is separated from the buzzer and USB cable.
- MPU6050 is fixed firmly.
- BMP180 and APDS9960 are disconnected.
- MaixCAM 2 and ESP32-S3 use separate data-capable USB connections.

## 6. Expected behavior / 预期现象

1. The wearable calibrates for about two seconds and then starts BLE; it continues normally with no wearable OLED attached.
2. The receiver OLED shows `BLE WAIT` while scanning and `BLE OK` after connection.
3. With ECG electrodes detached it shows `ECG LEADS OFF`; after attachment and threshold crossings it shows BPM.
4. ESP32-S3 LED blinks while scanning and stays on after connection.
5. Only an increase in `rep_count` produces one high beep. Fast, short-range, incomplete, repeated, and stale motion packets remain silent; their quality remains visible and recorded.
6. Filtered BPM above 150 for three consecutive valid measurements triggers one five-pulse alert. It rearms after three filtered values at or below 140 BPM. This classroom demo rule is not medically validated.
