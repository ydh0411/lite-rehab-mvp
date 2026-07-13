# LiteRehab-Fusion MVP

[English](README.md) | [中文](README_zh.md)

LiteRehab 是一个双开发板上肢康复原型。佩戴端 IMU 负责检测手臂运动，ESP32-S3 接收端提供声光反馈，MaixCAM 2 提供姿态识别画面。电脑端 Dashboard 融合两路数据，并保存同步后的训练记录。

本项目用于课程设计和原型演示，不是医疗器械，也不能替代理疗师。

## 项目能演示什么

- 使用佩戴式 MPU6050 识别并计数肘部屈伸和前臂旋转。
- 检测动作过快和活动范围不足。
- 使用 MaixCAM 2 姿态关键点估计肘关节活动范围和躯干代偿。
- 摄像头中断时保留 IMU-only 反馈，恢复画面后自动回到 Fusion。
- 记录每一条 IMU 数据及其时间上最接近的有效视觉特征。
- 默认自动加载使用小规模公开上肢 IMU 数据训练的 CNN-BiGRU；无需用户自行录制动作。

## 系统结构

```text
右臂佩戴端                               视觉端
MYOSA ESP32 + MPU6050                   MaixCAM 2
        │ BLE                               │ USB UVC（默认）
        ▼                                   │ 或 RTSP
ESP32-S3 接收端                             ▼
LED + 蜂鸣器 + USB 串口 ─────────────► Python Dashboard
                                       MediaPipe Pose
                                       规则/模型融合
                                       同步 CSV
```

MaixCAM 2 不需要与 ESP32 连接 GPIO。MaixCAM 2 和 ESP32-S3 接收端分别使用一条 USB 数据线连接电脑。

## 硬件清单

| 数量 | 元件 | 用途 |
|---:|---|---|
| 1 | MYOSA ESP32 WROOM-32E | 佩戴端控制与 BLE 外设 |
| 1 | ESP32-S3-DevKitC-1 N16R8 | BLE 接收和 USB 串口网关 |
| 1 | MPU6050 | 六轴手臂运动检测 |
| 1 | SSD1306 128×64 OLED | 显示连接、动作和计数 |
| 1 | MaixCAM 2 | UVC/RTSP 视觉输入 |
| 各 1 | 无源蜂鸣器、LED、220–330 Ω 电阻 | 接收端反馈 |
| 2 | 四芯 JST 线 | 佩戴端 I²C 级联 |
| 2–3 | USB 数据线 | 接收端、相机及佩戴端供电/烧录 |

### 接线

```text
佩戴端：
MYOSA I²C ── JST ── MPU6050 ── JST ── SSD1306 OLED

接收端：
GPIO2  ── 220–330 Ω ── LED 长脚；LED 短脚 ── GND
GPIO18 ── 100–330 Ω ── 无源蜂鸣器正极；蜂鸣器负极 ── GND

相机与电脑：
MaixCAM 2 Type-C ── USB 数据线 ── 电脑
ESP32-S3 原生 USB ── 另一条 USB 数据线 ── 电脑
```

MPU6050 应牢固固定在前臂背侧，X 轴指向手部，Z 轴朝向皮肤外侧。上电前请先阅读 [WIRING_GUIDE.md](WIRING_GUIDE.md)。

## 快速开始

### 1. 烧录两块 ESP32

```bash
source ~/.espressif/v6.0.2/esp-idf/export.sh

./scripts/flash_wearable.sh /dev/cu.usbserial-WEARABLE
./scripts/flash_receiver.sh /dev/cu.usbmodem-RECEIVER
```

本次 MaixCAM 2 更新不需要重新烧录两块 ESP32。

### 2. 安装电脑端环境

```bash
conda create -n literehab python=3.12 -y
conda activate literehab
pip install -r python/requirements.txt
```

macOS 弹出提示时需要允许摄像头权限。如果安装的 MediaPipe 使用 Tasks API，请将 `pose_landmarker_lite.task` 放入 `python/models/`。

### 3. 以 UVC 模式启动 MaixCAM 2

1. 在 MaixCAM 2 打开 `Settings → USB Settings`，启用 `UVC`。
2. 使用 Type-C 数据线将 MaixCAM 2 连接电脑。
3. 在 MaixVision 中打开 [maixcam2/main.py](maixcam2/main.py)。
4. 保持 `MODE = "uvc"`，运行文件。

先断开 MaixCAM 2 运行一次检测，再连接后运行一次。新增的编号通常就是 MaixCAM 2：

```bash
PYTHONPATH=python python scripts/probe_cameras.py
```

### 4. 启动右臂 Dashboard

```bash
PYTHON=python ./scripts/start_maixcam2_demo.sh <maixcam-index>
```

对应的完整命令为：

```bash
python python/run_dashboard.py \
  --port auto \
  --camera-source <maixcam-index> \
  --side right \
  --output python/sessions/maixcam2_demo.csv
```

左上角应显示 `Serial: connected`、`Camera: connected` 和 `Mode: Fusion`。如果仍显示 `IMU-only`，请后退一些，确保右肩、右肘、右手腕和右髋同时可见。

## RTSP 备用方案

电脑无法打开 UVC 设备时，可以改用 RTSP：

1. 将 MaixCAM 2 和电脑连接到同一网络。
2. 把 [maixcam2/main.py](maixcam2/main.py) 中的 `MODE` 改为 `"rtsp"`。
3. 在 MaixVision 中运行，复制终端打印的地址。
4. 使用该地址启动 Dashboard：

```bash
PYTHON=python ./scripts/start_maixcam2_demo.sh \
  rtsp://<device-ip>:8554/live
```

电脑端相机模块支持 `auto`、本地摄像头编号和 `rtsp://` 地址。画面中断后，程序会限制重连频率，并继续记录 IMU 数据。

## 演示流程

将 MaixCAM 2 横向放置在参与者正前方，距离约 1.5–2.0 m，高度与胸口接近。

1. 身体直立、右臂自然下垂。点击 Dashboard 窗口，在窗口获得键盘焦点后按一次小写 `b`，记录躯干基线。
2. 用 2–3 秒缓慢完成一次肘部屈伸并回到起始位置。
3. 肘部保持约 90°，固定上臂并旋转前臂。
4. 快速完成一次肘部屈伸，演示 `too_fast` 和两声低音。
5. 只做小幅度运动，演示 `insufficient_range`。
6. 屈肘时明显侧倾身体，演示躯干代偿提示。
7. 短暂遮挡相机。模式会切换到 `IMU-only`，恢复姿态后自动回到 `Fusion`。

Dashboard 按键：

| 按键 | 功能 |
|---|---|
| `b` | 重新设置中立位躯干基线 |
| `r` | 重置当前动作的活动范围 |
| `q` 或 `Esc` | 退出并关闭 CSV 文件 |

默认会话文件为 `python/sessions/maixcam2_demo.csv`。

## 识别与反馈

| 输出 | 来源 | 含义 |
|---|---|---|
| `elbow_flexion` | IMU 规则 | 前臂绕肘关节弯曲并返回 |
| `forearm_rotation` | IMU 规则 | 前臂绕自身长轴旋转 |
| `too_fast` | IMU 规则 | 峰值角速度超过设定范围 |
| `insufficient_range` | IMU 规则 | 积分得到的运动角度过小 |
| `trunk_compensation` | 视觉 | 肩部相对髋部的位移超过基线范围 |

固件规则仍是安全回退路径。Dashboard 默认加载 `python/models/imu_cnnbigru.pt`：该模型只使用 3 位公开参与者的小规模右腕 IMU 子集训练，使用 100 个采样点的窗口。静止状态由 ESP32 的 `idle` 规则门控，不需要用户自行录制训练数据。模型只用于课程演示，不能作为医疗准确性结论。

## 测试

运行完整检查：

```bash
./scripts/test_all.sh
```

该脚本会运行 C 运动/数据包测试、Python 测试、语法检查、Dashboard 冒烟测试，以及两块 ESP32 的固件构建。目前共有 3 个 C 主机测试和 49 个 Python 测试。

## 项目结构

```text
wearable/        MYOSA ESP32 佩戴端固件
receiver/        ESP32-S3 BLE 接收端固件
shared/          数据包、动作与反馈公共逻辑
python/          Dashboard、同步、模型、训练和测试
maixcam2/        MaixPy UVC/RTSP 相机程序
scripts/         构建、烧录、相机检测和演示脚本
tests/           C 语言主机测试
docs/            设计与实现记录
```

## 其他文档

- [MaixCAM 2 设置](maixcam2/README.md)
- [完整接线指南](WIRING_GUIDE.md)
- [分步演示指南](DEMO_GUIDE.md)
- [中英文元器件清单](COMPONENTS.md)

## 安全与范围

LiteRehab 不用于诊断、临床评分、治疗处方或无人监督的康复决策。演示过程中，如果参与者出现疼痛、头晕、麻木或其他异常不适，应立即停止。
