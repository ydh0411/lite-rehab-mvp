# LiteRehab-Fusion MVP 演示指导文档

## 系统架构

```text
┌──────────────────────────────┐     BLE      ┌──────────────────────┐
│  MYOSA ESP32 穿戴端          │ ◄──────────► │  ESP32-S3 接收端      │
│  MPU6050 六轴传感器           │   motion_    │  LED (GPIO2)          │
│  SSD1306 OLED 显示屏          │   packet     │  蜂鸣器 (GPIO18)       │
│  互补滤波 + 自适应阈值分类     │              │  CRC 校验 + 串口转发   │
└──────────────────────────────┘              └──────────┬───────────┘
                                                         │ USB Serial
                                                         ▼
                                              ┌──────────────────────┐
                                              │  Python Dashboard    │
                                              │  MediaPipe 姿态估计   │
                                              │  IMU 陀螺仪图表       │
                                              │  CNN-BiGRU 模型(可选) │
                                              │  CSV 会话记录         │
                                              └──────────────────────┘
```

## 识别状态

| 状态 | 英文标识 | 说明 |
|------|----------|------|
| 空闲 | `idle` | 无运动 |
| 前臂旋转 | `forearm_rotation` | 手腕绕前臂轴旋转 |
| 肘部屈伸 | `elbow_flexion` | 前臂绕肘关节弯曲/伸展 |

## 反馈质量

| 质量 | 英文标识 | 蜂鸣器 | 说明 |
|------|----------|--------|------|
| 良好 | `ok` | 一声高音 | 动作幅度和速度达标 |
| 过快 | `too_fast` | 两声低音 | 动作速度超标 |
| 幅度不足 | `insufficient_range` | 两声低音 | 活动范围不够 |
| 躯干代偿 | `trunk_compensation` | 视觉提示 | 肩部相对髋部偏移过大 |

---

## 一、硬件接线

### 1.1 穿戴端（MYOSA ESP32）

JST 级联顺序：

```text
MYOSA 主板 I2C 口 ── JST 4P 线 ──► MPU6050 I2C 口
       │
       └── JST 4P 线 ──► SSD1306 OLED I2C 口
```

- SDA = GPIO21，SCL = GPIO22（固件已定义，无需额外接线）
- MPU6050 固定在前臂背侧，X 轴指向手部，Z 轴朝外
- BMP180 和 APDS9960 不接
- 保留 USB-C 供电或使用移动电源

### 1.2 接收端（ESP32-S3-DevKitC-1）

面包板接线：

```text
LED:
  ESP32-S3 GPIO2 ── 220Ω 电阻 ── LED 长脚 (+)
  ESP32-S3 GND    ────────────── LED 短脚 (-)

蜂鸣器（无源）:
  ESP32-S3 GPIO18 ── 100Ω 电阻 ── 蜂鸣器 (+)
  ESP32-S3 GND     ────────────── 蜂鸣器 (-)
```

- 接收端使用原生 USB 口（标有 **USB**），非 UART 口
- GPIO19/20 保持空闲

### 1.3 供电

- 开发时：两个板子各接一个笔记本 USB 口
- 演示时：穿戴端可用移动电源供电，接收端保持笔记本供电

---

## 二、固件烧录

### 2.1 环境准备

```bash
source ~/.espressif/v6.0.2/esp-idf/export.sh
```

### 2.2 烧录穿戴端（ESP32）

```bash
cd lite_rehab_mvp/wearable
idf.py set-target esp32
idf.py -p /dev/cu.usbserial-* -b 460800 flash
```

- 芯片：ESP32-D0WD-V3
- 波特率 460800 即可，通常情况下无需手动进入下载模式

### 2.3 烧录接收端（ESP32-S3）

**重要**：ESP32-S3 原生 USB-Serial/JTAG 在烧录时可能不稳定。若出现 `No more data to read` 错误，使用以下手动下载流程：

```bash
cd lite_rehab_mvp/receiver
idf.py set-target esp32s3
```

1. 按住 BOOT 键不放
2. 点按 RST 键
3. 松开 BOOT 键
4. 立即执行：

```bash
python -m esptool --chip esp32s3 --before no-reset --after no-reset \
  -p /dev/cu.usbmodem* -b 115200 write-flash \
  0x0 build/bootloader/bootloader.bin \
  0x8000 build/partition_table/partition-table.bin \
  0x10000 build/literehab_receiver.bin
```

5. 烧录完成后按 RST 键启动固件

> **注意**：烧录前确保没有其他程序占用串口（关闭 dashboard、monitor 等）。

---

## 三、Python 环境

### 3.1 安装依赖

```bash
conda create -n literehab python=3.12 -y
conda activate literehab
cd lite_rehab_mvp/python
pip install -r requirements.txt
```

### 3.2 下载 MediaPipe 模型（首次）

```bash
mkdir -p models
# 自动下载 pose_landmarker_lite.task（约 5.6 MB）
python -c "import mediapipe as mp; print('MediaPipe OK')"
```

如果 MediaPipe Tasks API 模型缺失，dashboard 会自动退化为 IMU-only 模式。

---

## 四、启动 Dashboard

### 4.1 基本启动

```bash
cd lite_rehab_mvp/python
python run_dashboard.py --port auto --camera 0 --side left \
  --output sessions/demo.csv
```

- `--port auto`：自动查找串口
- `--camera 0`：使用默认摄像头
- `--side left/right`：选择佩戴传感器和训练的患侧
- `--output`：CSV 输出路径

### 4.2 加载深度学习模型（可选）

```bash
python run_dashboard.py --port auto --model models/imu_cnn_bigru.pt

# 真正的视觉—IMU双分支模型（采集并训练后）
python run_dashboard.py --port auto --side left \
  --fusion-model models/multimodal_cnn_bigru.pt
```

### 4.3 操作按键

| 按键 | 功能 |
|------|------|
| `q` / `Esc` | 退出 |
| `b` | 重新捕获躯干基准姿态 |
| `r` | 重置当前 repetition 的活动范围 |

---

## 五、演示流程

### 步骤 1：上电检查

1. 穿戴端 OLED 显示 `KEEP STILL` → `CALIBRATE`（约 2 秒）
2. 校准完成后显示 `LITEREHAB` + 状态 + 次数
3. 接收端 LED 闪烁（扫描中）
4. BLE 连接成功后 LED 常亮，OLED 显示 `BLE OK`

### 步骤 2：启动 Dashboard

运行 `run_dashboard.py`，确认窗口标题为 `LiteRehab-Fusion MVP`，界面包含：

- 左侧：摄像头画面 + MediaPipe 姿态关键点
- 右侧：IMU 陀螺仪三轴实时曲线（X红 Y绿 Z蓝）
- 左上叠加信息：Mode / Exercise / Repetitions / Feedback / Serial 状态

### 步骤 3：演示动作

#### 前臂旋转（forearm_rotation）

- 手臂自然下垂，掌心朝内
- 旋转前臂使掌心朝前 → 回到原位
- OLED 显示 `ROTATE`，完成后蜂鸣器响一声

#### 肘部屈伸（elbow_flexion）

- 手臂自然下垂
- 弯曲肘部将前臂抬起 → 放下回原位
- OLED 显示 `ELBOW`，完成后蜂鸣器响一声

### 步骤 4：展示反馈

- **过快动作**：快速甩动手臂 → OLED 显示 `FAST` + 两声低音
- **幅度不足**：小幅度晃动 → OLED 显示 `RANGE` + 两声低音
- **躯干代偿**：弯曲时倾斜身体 → Dashboard 提示 `Avoid trunk compensation`

### 步骤 5：展示数据记录

演示结束后，检查 CSV 记录：

```bash
head -5 sessions/demo.csv
```

包含字段：设备与接收时间戳、加速度计三轴、陀螺仪三轴、状态、次数、质量、左右侧视觉角度/速度/可见度、视觉有效标记、模型输出、subject 和人工标签。每条已接收 IMU 数据都会记录；找不到相邻视频帧时视觉字段保留为显式缺失标记。

---

## 六、算法特性

### 6.1 互补滤波器（Wang 2026）

- 陀螺仪短时积分 + 加速度计长时重力修正
- 输出稳定的 Roll/Pitch 姿态角，消除陀螺仪漂移
- 参数：`comp_alpha = 0.98`（98% 信任陀螺仪，2% 加速度计修正）

### 6.2 自适应阈值（Khalilipour 2025）

- 跟踪信号 RMS，动态调整进入/退出阈值
- 仅在静止噪声范围内更新，动作本身不会抬高反向阈值
- 范围：25-150 dps
- 适应不同速度的运动，避免固定阈值误触发或漏触发

### 6.3 加速度计辅助方向判断

- 前臂旋转时重力矢量在 X 轴变化大
- 肘部屈伸时重力矢量在 Y 轴变化大
- 结合陀螺仪主导比例 + 加速度计方向确认

### 6.4 CNN-BiGRU 模型（Obukhov et al. 2025）

- 架构：3×Conv1D + BiGRU + FC
- 参数量：~423K，CPU 推理 5-10ms
- 输入：100 采样窗口 × 6 通道（3 加速度 + 3 陀螺仪）
- 需要标注数据训练后使用（`--arch cnn_bigru`）

---

## 七、训练数据采集

```bash
# 每人每类采集 30 秒
python collect_data.py --port auto --subject S01 --label idle --seconds 30
python collect_data.py --port auto --subject S01 --label forearm_rotation --seconds 30
python collect_data.py --port auto --subject S01 --label elbow_flexion --seconds 30
```

至少采集 3 人数据，保留 1 人作为测试集。

### 训练 CNN-BiGRU

```bash
python train_1d_cnn.py --data data --holdout-subject S03 \
  --arch cnn_bigru --epochs 50 --output models/imu_cnn_bigru.pt
```

### 采集和训练视觉—IMU融合模型

每个文件只使用一个人工 exercise/quality 标签组合：

```bash
python run_dashboard.py --port auto --side left --subject S01 \
  --label-exercise elbow_flexion --label-quality ok \
  --output multimodal_data/S01_elbow_ok.csv

python run_dashboard.py --port auto --side left --subject S01 \
  --label-exercise elbow_flexion --label-quality too_fast \
  --output multimodal_data/S01_elbow_fast.csv

python train_multimodal.py --data multimodal_data --holdout-subject S03 \
  --epochs 30 --output models/multimodal_cnn_bigru.pt
```

没有 checkpoint 或模型置信度不足时，Dashboard 自动回退到可直接运行的固件规则，不会阻止演示。

---

## 八、常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| OLED 显示 `MPU ERROR` | MPU6050 未检测到 | 检查 JST 连接，I2C 地址应为 0x68 或 0x69 |
| OLED 一直 `BLE WAIT` | BLE 未连接 | 检查接收端是否烧录并上电，两板距离不超过 5 米 |
| Dashboard 显示 `IMU-only` | 摄像头/MediaPipe 不可用 | 检查摄像头权限，确认 MediaPipe 模型已下载 |
| Dashboard 显示 `connecting` | 串口未连接 | 检查端口号，关闭其他占用串口的程序 |
| ESP32-S3 烧录失败 | 原生 USB 不稳定 | 使用手动下载模式（BOOT+RST），波特率降至 115200 |
| 蜂鸣器不响 | GPIO18 接线或占空比问题 | 检查 LEDC PWM 配置，确认 GPIO18 未被占用 |
| 计数不准确 | 阈值不适合当前运动幅度 | 调整 `motion_default_config()` 中的阈值参数 |

---

## 九、安全声明

此为工程原型，不用于临床诊断、处方治疗、临床评分预测或替代物理治疗师。
