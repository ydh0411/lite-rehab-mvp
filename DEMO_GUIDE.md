# LiteRehab-Fusion MVP 演示指导文档

## 系统架构

```text
┌──────────────────────────────┐     BLE      ┌──────────────────────┐
│  MYOSA ESP32 穿戴端          │ ◄──────────► │  ESP32-S3 接收端      │
│  MPU6050 六轴传感器           │   motion_    │  OLED (GPIO8/9)       │
│  互补滤波 + 自适应阈值分类     │   packet     │  CJMCU-8232 (GPIO4/5/6)│
│  轻量刚性固定，无 OLED 尾线    │              │  LED + 蜂鸣器 + 串口   │
└──────────────────────────────┘              └──────────┬───────────┘
                                                         │ USB Serial
                                                         ▼
                                              ┌──────────────────────┐
                                              │  Python Dashboard    │
                                              │  MediaPipe 姿态估计   │
                                              │  ECG 波形 + BPM       │
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
| 过快 | `too_fast` | 静音 | 动作速度超标；质量状态仍显示和记录 |
| 幅度不足 | `insufficient_range` | 静音 | 活动范围不够；质量状态仍显示和记录 |
| 躯干代偿 | `trunk_compensation` | 视觉提示 | 肩部相对髋部偏移过大 |

---

## 一、硬件接线

### 1.1 穿戴端（MYOSA ESP32）

轻量穿戴连接：

```text
MYOSA 主板 I2C 口 ── 一根短 JST 4P 线 ──► MPU6050 I2C 口
```

- SDA = GPIO21，SCL = GPIO22（固件已定义，无需额外接线）
- OLED 移到 S3；佩戴端固件找不到 OLED 时会继续运行
- MYOSA 与 MPU6050 固定在同一块硬质底板，JST 线折成小弧后用胶带固定
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

OLED:
  ESP32-S3 3V3   ── OLED VCC
  ESP32-S3 GND   ── OLED GND
  ESP32-S3 GPIO8 ── OLED SDA
  ESP32-S3 GPIO9 ── OLED SCL

CJMCU-8232:
  ESP32-S3 3V3   ── 3.3V + SDN
  ESP32-S3 GND   ── GND
  ESP32-S3 GPIO4 ── OUTPUT
  ESP32-S3 GPIO5 ── LO+
  ESP32-S3 GPIO6 ── LO-
```

- 接收端使用原生 USB 口（标有 **USB**），非 UART 口
- GPIO19/20 保持空闲
- N16R8 不使用 GPIO35/36/37；同学 Arduino 参考中的 GPIO36 不能作为 S3 ADC
- OLED 只有 JST 口时使用 JST 转杜邦转接板，并按丝印确认 3V3/GND/SDA/SCL
- CJMCU 只接 3.3 V，OUTPUT 线尽量短并远离 GPIO18 蜂鸣器线
- RA/LA/RL 按电极线标签连接，不要只看颜色

### 1.3 MaixCAM 2 相机

不需要连接 GPIO 或面包板。使用两条独立 USB 数据线：

```text
MaixCAM 2 Type-C 数据口 ──► 笔记本 USB（供电 + UVC 视频）
ESP32-S3 原生 USB 口     ──► 另一个笔记本 USB（供电 + 串口）
MYOSA 穿戴端             ── BLE ──► ESP32-S3
```

1. 在 MaixCAM 2 打开 **Settings → USB Settings → UVC**。
2. 用 MaixVision 打开 `maixcam2/main.py`，确认 `MODE = "uvc"`，点击 Run。
3. 相机横放在患者前方 1.5–2.0 m、胸口高度；右臂演示时，右肩、肘、手腕和右髋必须完整可见。

### 1.4 供电

- 未贴 ECG 电极时：两个板子可各接一个笔记本 USB 口
- 演示时：穿戴端可用移动电源供电，接收端保持笔记本供电
- ECG 电极接触人体时：笔记本使用电池并拔掉交流充电器；本项目不是医疗隔离设备

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

课堂展示优先使用本地网页界面；原 OpenCV Dashboard 仍保留，便于回退和调试。

### 4.0 本地网页界面（课堂展示推荐）

```bash
cd lite_rehab_mvp

# MaixCAM2 RTSP
./scripts/start_web_demo.sh rtsp://10.203.102.1:8554/live

# 或 MaixCAM2 UVC 编号
./scripts/start_web_demo.sh <maixcam-index>
```

脚本会检查 `web/dist`，只在前端源码更新或尚未构建时运行 Vite 构建，然后启动 `http://127.0.0.1:8000` 并打开浏览器。

- **Live Training**：摄像头骨架、动作、次数、ROM、实时反馈、ECG 与硬件状态
- **Session History**：按参与者和动作筛选本机 CSV 会话
- **Session Report**：次数、动作质量、ROM、BPM 与数据完整性；可通过浏览器打印为 PDF

网页关闭不等于停止采集。演示结束后回到终端按 `Ctrl+C`，运行时会关闭串口、摄像头和正在写入的文件。网页与报告均为工程原型，不用于临床判断。

### 4.1 MaixCAM 2 UVC 启动（推荐）

```bash
cd lite_rehab_mvp
# 分别在 MaixCAM 2 断开和连接后运行一次，找新增的相机编号
PYTHONPATH=python python scripts/probe_cameras.py

# 右臂演示；把 <maixcam-index> 替换为新增编号
./scripts/start_maixcam2_demo.sh <maixcam-index>
```

- `--port auto`：自动查找串口
- `--camera-source <index>`：使用 MaixCAM 2 的 UVC 编号
- `--side left/right`：选择佩戴传感器和训练的患侧
- `--output`：CSV 输出路径

如 UVC 无法工作，修改 `maixcam2/main.py` 为 `MODE = "rtsp"`，运行后复制 MaixVision 终端打印的 URL：

```bash
./scripts/start_maixcam2_demo.sh rtsp://<device-ip>:8554/live
```

### 4.2 CNN-BiGRU 自动加载

```bash
./scripts/start_maixcam2_demo.sh rtsp://10.203.102.1:8554/live
```

启动脚本会自动加载 `python/models/imu_cnnbigru.pt`，不需要再填写
`--model`。模型只使用公开数据训练；静止状态由 ESP32 规则门控，因此不需要
自行录制动作数据。如果文件缺失，Dashboard 会明确报错并停止，而不会继续显示
`IMU CNN: not loaded`。

### 4.3 操作按键

| 按键 | 功能 |
|------|------|
| `q` / `Esc` | 退出 |
| `b` | 重新捕获躯干基准姿态 |
| `r` | 重置当前 repetition 的活动范围 |

---

## 五、演示流程

### 步骤 1：上电检查

1. 穿戴端上电后静置约 2 秒完成 MPU6050 校准；无 OLED 也会继续
2. 接收端 OLED 显示 `LITEREHAB`、`BLE WAIT` 和 `ECG LEADS OFF`
3. 接收端 LED 闪烁（扫描中），BLE 连接后常亮且 OLED 显示 `BLE OK`
4. 贴好 ECG 电极并保持静止，OLED 变为 BPM；若仍为 `LEADS OFF`，先检查电极与 GPIO5/6

### 步骤 2：启动 Dashboard

运行后确认窗口标题为 `LiteRehab-Fusion MVP`，先检查顶部状态标签：

- `SERIAL` 和 `CAMERA` 标签为绿色
- 模式标签显示 `FUSION`
- 若模式显示 `IMU ONLY`，后退一点并保持右侧肩、肘、腕、髋完整入镜

界面包含：

- 顶部：串口、摄像头和融合模式健康标签，绿色表示正常，橙色表示连接中或降级，红色表示不可用
- 左侧：摄像头画面、MediaPipe 姿态关键点、当前动作和高优先级训练反馈
- 右侧：训练次数、当前动作、ROM、模型状态，以及实时 ECG 波形、BPM 和导联状态
- 底部反馈条：绿色表示动作良好，橙色提示减速或增加幅度，红色提示避免躯干代偿

### 步骤 3：设定基线

点击 Dashboard 画面使窗口获得键盘焦点。右臂自然下垂、身体直立不动时，按小写 `b` 一次；不要在终端里输入 `b`。

### 步骤 4：演示动作

#### 前臂旋转（forearm_rotation）

- 手臂自然下垂，掌心朝内
- 旋转前臂使掌心朝前 → 回到原位
- 接收端 OLED 显示 `ROTATE`，完成后蜂鸣器响一声

#### 肘部屈伸（elbow_flexion）

- 手臂自然下垂
- 弯曲肘部将前臂抬起 → 放下回原位
- 接收端 OLED 显示 `ELBOW`，完成后蜂鸣器响一声

### 步骤 5：展示反馈

- **完整有效动作**：完成一次被计数的动作 → `rep_count` 增加，接收端发出一声高音
- **过快动作**：快速甩动手臂 → 接收端 OLED 显示 `FAST`，蜂鸣器保持静音
- **幅度不足**：小幅度晃动 → 接收端 OLED 显示 `RANGE`，蜂鸣器保持静音
- **躯干代偿**：弯曲时倾斜身体 → Dashboard 提示 `Avoid trunk compensation`
- **ECG**：Dashboard 显示连续波形和滤波 BPM；BPM 连续 3 次高于 150 时蜂鸣器快速提示五次且只触发一次，连续 3 次降至 140 或以下后重新允许报警。该课堂演示规则未经医学验证，也不改变动作识别或质量反馈。

### 步骤 6：展示数据记录

演示结束后，检查 CSV 记录：

```bash
head -5 sessions/demo.csv
```

主会话 CSV 包含设备/接收时间、六轴 IMU、状态、次数、质量、视觉角度/速度/可见度、模型输出、subject 和人工标签。每条 IMU 都会记录，视觉缺失显式保留。

同目录还会生成 `<主文件名>_ecg.csv`，字段为 `t_ms,received_s,raw_adc,bpm,leads_connected,beat,high_bpm_alert`。ECG 文件仅用于波形展示和后续分析，不进入当前 CNN、重复计数或动作质量决策。

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

### 6.4 CNN-BiGRU 模型

- 架构：3×Conv1D + BiGRU + FC
- 参数量：~423K，CPU 推理 5-10ms
- 输入：100 采样窗口 × 6 通道（3 加速度 + 3 陀螺仪）
- 当前检查点使用 3 位公开参与者、3 种上肢动作的 7,600 个采样点训练
- 静止状态使用 ESP32 规则门控，不使用用户自录数据

---

## 七、模型数据来源与可选重训

当前演示不需要执行以下自录步骤。模型已使用公开数据集
<https://doi.org/10.17632/s86tdtmcc2.1> 的小规模子集训练完成。

仅当以后希望针对特定佩戴者提高准确率时，才需要自行采集：

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

当前默认检查点缺失时 Dashboard 会明确报错；运行过程中仍以固件规则作为安全回退。公开数据模型只用于课程演示，不代表临床准确性。

---

## 八、常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| 接收端 OLED 黑屏 | GPIO8/9 或电源顺序错误 | 断电核对 OLED 丝印/JST 转接和地址 0x3C；其他功能可继续 |
| OLED 一直 `BLE WAIT` | BLE 未连接 | 检查佩戴端是否烧录并上电，两板距离不超过 5 米 |
| OLED/Dashboard 一直 `LEADS OFF` | 电极或 LO+/LO- 接线问题 | 检查 RA/LA/RL 接触与 GPIO5/6，清洁干燥皮肤 |
| ECG 波形平直或噪声大 | OUTPUT 错接/线长/电极松/蜂鸣器串扰 | 核对 GPIO4，缩短并分开模拟线，保持身体静止 |
| Dashboard 显示 `IMU-only` | 摄像头/MediaPipe 不可用 | 检查摄像头权限，确认 MediaPipe 模型已下载 |
| MaixCAM 2 不在相机列表 | UVC 未开启或线缆仅充电 | 开启 UVC，改用数据线，重新运行 `main.py` 和 `probe_cameras.py` |
| MaixCAM 2 画面可见但仍为 `IMU-only` | 右侧关键点不可见 | 后退到 1.5–2.0 m，确保右肩、肘、腕和右髋都在画面内 |
| UVC 反复断开 | USB 供电或端口不稳定 | 换数据线/USB 口，或改用 RTSP 备用路径 |
| Dashboard 显示 `connecting` | 串口未连接 | 检查端口号，关闭其他占用串口的程序 |
| ESP32-S3 烧录失败 | 原生 USB 不稳定 | 使用手动下载模式（BOOT+RST），波特率降至 115200 |
| 蜂鸣器不响 | GPIO18 接线或占空比问题 | 检查 LEDC PWM 配置，确认 GPIO18 未被占用 |
| 计数不准确 | 阈值不适合当前运动幅度 | 调整 `motion_default_config()` 中的阈值参数 |

---

## 九、安全声明

此为工程原型，不用于临床诊断、处方治疗、临床评分预测或替代物理治疗师。
