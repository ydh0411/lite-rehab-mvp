# LiteRehab 最终 Demo 完整运行手册

本手册把两个界面写成独立启动入口：

- 电脑端：Web Dashboard 大屏；
- 手机端：iPhone LiteRehab App。

可以只启动电脑端、只启动手机端，或让两端同时显示。必须理解：

- 电脑端需要 Mac Python 后端；
- 手机端也需要 Mac Python 后端，iPhone 不直接连接 ESP32 或 MaixCAM；
- 两端同时使用时，只启动一个带 `--mobile` 的 Mac 后端；
- 电脑浏览器和 iPhone 都连接这个后端，因此共享同一 Session；
- 不要同时运行“电脑端后端”和“手机端后端”，否则会争抢串口和摄像头；
- 默认演示右臂；
- MaixCAM 2 默认使用 RTSP over USB NCM；
- ECG 是可选扩展，不参与动作识别。

详细接线图见 [`WIRING_GUIDE.md`](WIRING_GUIDE.md)。

---

## 0. 是否需要重新烧录

### 需要烧录

- 第一次使用开发板；
- 更新了 `wearable/`、`receiver/` 或 `shared/`；
- 开发板当前不是 LiteRehab 固件；
- 固件行为异常，需要重新写入确认。

当前版本修正了接收端蜂鸣器语义，因此第一次使用本版本时必须重新烧录接收端。建议两块板一起重新烧录，保证版本一致。

### 不需要烧录

如果开发板已经运行当前版本，普通 Demo 只需要：

1. 给接收端和穿戴端上电；
2. 运行 MaixCAM；
3. 启动 Mac 后端；
4. 电脑端模式打开 Web；
5. 手机端模式在 iPhone 扫码配对；
6. 双端模式同时完成第 4、5 步，但仍只运行一个后端。

这种情况直接看[第 5 节](#5-每次-demo-的启动流程)。

---

## 1. 新电脑首次准备

### 1.1 获取正确代码

```bash
git clone https://github.com/ydh0411/lite-rehab-mvp.git
cd lite-rehab-mvp
git fetch origin
git switch --track origin/codex/final-project-hardening
```

如果分支已经存在：

```bash
git switch codex/final-project-hardening
git pull --ff-only
```

确认位于仓库根目录：

```bash
pwd
test -f python/run_web_dashboard.py
test -f scripts/demo_doctor.sh
```

两个 `test` 命令没有报错即为正确。

### 1.2 Python 3.12

```bash
conda create -n literehab python=3.12 -y
conda activate literehab
python --version
python -m pip install -r python/requirements.txt
```

本手册统一要求 `python --version` 显示 Python 3.12.x。项目部分组件可在
3.10–3.11 工作，但最终演示不要临时更换版本，也不要使用 Python 3.13/3.14。

以后每次新开终端：

```bash
cd /path/to/lite-rehab-mvp
conda activate literehab
```

### 1.3 Web 前端

```bash
npm --prefix web ci
npm --prefix web run build
```

应生成：

```text
web/dist/index.html
```

### 1.4 ESP-IDF

项目验证版本为 ESP-IDF 6.0.2。安装后任选一种配置：

```bash
source /path/to/esp-idf/export.sh
```

或：

```bash
export IDF_PATH="/path/to/esp-idf"
```

或：

```bash
export IDF_EXPORT="/path/to/esp-idf/export.sh"
```

构建验证：

```bash
./scripts/build_all.sh
```

必须看到 wearable 和 receiver 两个固件均构建成功。

### 1.5 iPhone App 首次安装

```bash
brew install xcodegen
cd ios
xcodegen generate
open LiteRehab.xcodeproj
```

在 Xcode 中：

1. 选择 `LiteRehab` Target；
2. 打开 **Signing & Capabilities**；
3. 选择自己的 Personal Team；
4. 连接 iOS 17 或更高版本的 iPhone；
5. 在 iPhone 开启 Developer Mode；
6. 选择真实 iPhone 作为运行目标；
7. 点击 Run。

安装完成后关闭 Xcode不影响日常 Demo。免费 Personal Team 签名到期后才需要重新 Run。

---

## 2. 上电前接线与安全检查

所有接线调整必须先断开 USB 电源。

### 2.1 穿戴端

- MYOSA ESP32 通过短 JST 4P 线连接 MPU6050；
- MPU6050 固定在右前臂背侧；
- X 轴指向手部；
- Z 轴朝外；
- 主板和 MPU6050 固定在同一硬质底板；
- JST 线不能悬空摆动；
- BMP180、APDS9960、穿戴端 OLED 不接。

### 2.2 接收端

| 功能 | ESP32-S3 |
|---|---:|
| LED | GPIO2，经 220–330 Ω |
| ECG OUTPUT | GPIO4 |
| ECG LO+ | GPIO5 |
| ECG LO- | GPIO6 |
| OLED SDA | GPIO8 |
| OLED SCL | GPIO9 |
| 无源蜂鸣器 | GPIO18，经 100–330 Ω |

确认：

- OLED 与 CJMCU-8232 只使用 3.3 V；
- GPIO19/20 保持空闲；
- 使用 ESP32-S3 标有 **USB** 的原生 USB 口；
- ECG OUTPUT 线与蜂鸣器线分开；
- ECG 电极接触人体时，Mac 使用电池并拔掉交流充电器；
- 本系统不是医疗器械，也不是医疗隔离设备。

---

## 3. 识别真实串口

不要把 `/dev/cu.usbserial-*` 通配符直接交给烧录脚本。

查看全部串口：

```bash
conda activate literehab
python -m serial.tools.list_ports -v
```

最可靠的识别方法：

1. 拔掉两块板，运行一次端口列表；
2. 只插入穿戴端，再运行一次；
3. 新出现的是穿戴端；
4. 拔掉穿戴端，只插入接收端原生 USB；
5. 再运行一次，新出现的是接收端。

常见端口：

```text
macOS 穿戴端：/dev/cu.usbserial-XXXX
macOS 接收端：/dev/cu.usbmodemXXXX
Linux 穿戴端：/dev/ttyUSB0
Linux 接收端：/dev/ttyACM0
```

保存真实值：

```bash
export WEARABLE_PORT="/dev/cu.usbserial-替换为真实值"
export RECEIVER_PORT="/dev/cu.usbmodemXXXX"
```

上面的 `XXXX` 只是占位符。必须从端口列表复制完整原值，不要自行添加或删除连字符。

检查：

```bash
test -e "$WEARABLE_PORT" && echo "Wearable port OK"
test -e "$RECEIVER_PORT" && echo "Receiver port OK"
```

重新插拔后端口可能改变，烧录或启动前应重新确认。

---

## 4. 需要烧录时的完整步骤

### 4.1 先关闭串口占用

关闭：

- Web Dashboard；
- `idf.py monitor`；
- Arduino Serial Monitor；
- VS Code/PlatformIO Monitor；
- 其他读取同一串口的 Python 程序。

### 4.2 构建

```bash
cd /path/to/lite-rehab-mvp
conda activate literehab
./scripts/build_all.sh
```

### 4.3 烧录穿戴端

优先使用项目脚本。下面列出的“等价命令”只有在当前终端已经 source ESP-IDF
`export.sh` 后才能直接运行；只设置 `IDF_PATH`/`IDF_EXPORT` 时，项目脚本会负责加载环境。

```bash
./scripts/flash_wearable.sh "$WEARABLE_PORT"
```

等价命令：

```bash
idf.py -C wearable -p "$WEARABLE_PORT" -b 460800 flash
```

正常结束会出现：

```text
Hash of data verified.
Leaving...
Hard resetting via RTS pin...
```

烧录后保持穿戴端静止至少 2 秒，让 MPU6050 完成零偏校准。

### 4.4 烧录接收端

```bash
./scripts/flash_receiver.sh "$RECEIVER_PORT"
```

等价命令：

```bash
idf.py -C receiver -p "$RECEIVER_PORT" -b 460800 flash
```

### 4.5 ESP32-S3 烧录失败

若出现 `No more data to read` 或无法复位：

1. 按住 BOOT；
2. 短按 RST；部分开发板把该键标成 EN；
3. 松开 BOOT；
4. 重新运行端口列表；
5. 更新 `$RECEIVER_PORT`；
6. 用低波特率烧录：

```bash
BAUD=115200 ./scripts/flash_receiver.sh "$RECEIVER_PORT"
```

烧录完成后按一次 RST/EN。

仍失败时，再次执行“按住 BOOT → 短按 RST/EN → 松开 BOOT”，重新确认下载模式
下的端口，然后运行：

```bash
python -m esptool --chip esp32s3 \
  --before no-reset --after no-reset \
  -p "$RECEIVER_PORT" -b 115200 write-flash \
  0x0 receiver/build/bootloader/bootloader.bin \
  0x8000 receiver/build/partition_table/partition-table.bin \
  0x10000 receiver/build/literehab_receiver.bin
```

完成后按 RST/EN。

### 4.6 可选日志确认

```bash
source scripts/common.sh
literehab_load_esp_idf
idf.py -C receiver -p "$RECEIVER_PORT" monitor
```

预期：

```text
# LiteRehab receiver ready
# BLE connected
IMU,...
ECG,...
```

按 `Ctrl+]` 退出 Monitor。启动 Dashboard 前必须退出，否则串口会被占用。

---

## 5. 每次 Demo 的启动流程

先完成相机、开发板、端口和自检，再从 5.6 的三种启动方式中选择一种。

### 5.1 Mac、iPhone 与网络

1. Mac 与 iPhone 连接同一个可信 Wi-Fi 或手机热点；
2. 不使用有客户端隔离的公共 Wi-Fi；
3. macOS 防火墙弹窗出现时允许 Python 接受局域网连接；
4. MaixCAM 可通过 USB NCM 使用独立的 `10.203.102.x` 网络；
5. 同一 Mac 可以同时连接 Wi-Fi 给 iPhone、连接 USB NCM 给 MaixCAM。

### 5.2 启动 MaixCAM RTSP

1. 用数据线连接 MaixCAM；
2. 如系统要求，启用 USB NCM/network；
3. 在 MaixVision 打开 `maixcam2/main.py`；
4. 确认：

```python
MODE = "rtsp"
```

5. 点击 Run；
6. 复制打印的 URL。

常见 URL：

```text
rtsp://10.203.102.1:8554/live
```

Mac 终端：

```bash
export CAMERA_RTSP="rtsp://10.203.102.1:8554/live"
```

若输出 `rtsp://0.0.0.0:8554/live`，必须把 `0.0.0.0` 换成 MaixCAM 的真实 USB NCM 或局域网 IP。
优先在 MaixVision 的设备信息/网络设置中查看地址，也可以在 Mac 运行 `arp -a`
查看新增设备。项目常见 USB NCM 地址为 `10.203.102.1`，但应以当前设备实际地址为准。

可选检查：

```bash
ping -c 3 10.203.102.1
```

### 5.3 上电顺序

1. 接收端原生 USB 连接 Mac；
2. OLED 显示 `LITEREHAB`、`BLE WAIT`；
3. 穿戴端上电；
4. 穿戴端静置至少 2 秒；
5. 接收端 LED 从闪烁变为常亮；
6. OLED 变为 `BLE OK`。

若一直 `BLE WAIT`：

1. 穿戴端断电；
2. 接收端按 RST；
3. 穿戴端重新上电并静置；
4. 两板保持在 1–2 m 内。

### 5.4 确认端口

```bash
python -m serial.tools.list_ports -v
export RECEIVER_PORT="/dev/cu.usbmodemXXXX"
```

只有手机端或双端同步模式需要 Mac Wi-Fi IP：

```bash
export MAC_IP="$(ipconfig getifaddr en0)"
echo "$MAC_IP"
```

如果为空，使用 Mac 当前实际联网接口或在网络设置中查看：

```bash
export MAC_IP="替换为Mac真实局域网IP"
```

`MAC_IP` 必须是 iPhone 能访问的地址，不能填：

- `127.0.0.1`；
- `0.0.0.0`；
- MaixCAM 的 IP。

### 5.5 自检

```bash
cd /path/to/lite-rehab-mvp
conda activate literehab
./scripts/demo_doctor.sh
```

理想结果：

```text
Preflight summary: 0 failure(s), 0 warning(s)
```

出现 failure 必须先解决。若仅提示没有 USB 串口，重新检查接收端和 `$RECEIVER_PORT`。
正式动作 Demo 中，“没有 USB 串口”不是可接受 warning；“ESP-IDF 不可用”只有在本次
确定不需要重新烧录时才可接受。其他 warning 应先理解原因再继续。

### 5.6 方式 A：只启动电脑端 Web

此方式不使用 iPhone，不产生手机配对二维码：

```bash
PYTHON=python ./scripts/start_web_demo.sh "$CAMERA_RTSP" \
  --port "$RECEIVER_PORT" \
  --side right \
  --sessions-dir python/sessions \
  --model python/models/imu_cnnbigru.pt
```

脚本会启动 Mac 后端，并自动打开：

```text
http://127.0.0.1:8000
```

电脑端的 Start session、Stop session、Recapture baseline、Reset range 均可直接使用。

### 5.7 方式 B：只启动手机端

“手机端单独使用”仍然需要 Mac 在后台运行硬件与推理服务，但不需要打开电脑浏览器。

先确认 `$MAC_IP`：

```bash
echo "$MAC_IP"
```

启动手机后端：

```bash
PYTHON=python ./scripts/start_web_demo.sh "$CAMERA_RTSP" \
  --host 0.0.0.0 \
  --web-port 8000 \
  --mobile \
  --advertised-host "$MAC_IP" \
  --no-browser \
  --port "$RECEIVER_PORT" \
  --side right \
  --sessions-dir python/sessions \
  --model python/models/imu_cnnbigru.pt
```

终端必须保持运行。正常会显示：

- `Mobile server: http://<MAC_IP>:8000`；
- 配对二维码；
- Uvicorn 正在监听；
- 没有 runtime failure。

然后在 iPhone：

1. 打开 LiteRehab；
2. 点击 **Pair with Mac**；
3. 扫描终端二维码；
4. 确认 Mac connection 与 Motion sensor 为 Ready；
5. 输入 Participant ID；
6. 在 iPhone Start/Finish。

如果此前配对过旧地址，在 Settings 中 Disconnect/Repair 后重新扫码。

### 5.8 方式 C：电脑端与手机端同时显示

不要再运行方式 A 的命令。只运行一次方式 B 的 `--mobile` 后端，然后额外在 Mac 打开 Web：

```text
http://127.0.0.1:8000
```

也可以运行：

```bash
open http://127.0.0.1:8000
```

此时：

- Mac Web 连接 `127.0.0.1:8000`；
- iPhone 连接二维码中的 `http://<MAC_IP>:8000`；
- 两者实际连接同一个进程和同一个 Runtime；
- 任一端启动 Session，另一端会观察到 Recording；
- 任一端结束 Session，另一端会观察到停止。

为了避免重复命令，双端演示建议固定：

- iPhone 负责 Start Session 和 Finish Session；
- 电脑 Web 负责大屏展示与结束后报告；
- 电脑端不要再次点击 Start/Stop。

这只是操作约定，不是系统限制。如果选择电脑控制，也可以只在 Web Start/Stop，iPhone 会同步观察；关键是每次只由一端发命令。

### 5.9 各模式的正常界面

电脑端应显示：

- Serial 为 connected；
- Camera 为 `connected: rtsp://...`；
- 实时视频与人体关键点；
- 动作、次数、ROM、反馈；
- ECG leads off 或实时波形。

手机端应显示：

- Mac connection 为 connected；
- Motion sensor 为 Ready；
- 相机画面或相机状态；
- 动作、次数、ROM、反馈和 ECG。

双端模式开始 Session 后，应同时显示：

- 同一动作名称；
- 同一次数；
- 相同反馈；
- 相同 ROM；
- 相同 ECG/BPM 状态；
- 相同摄像头画面或接近的最新帧。

验证方法：

1. 轻微移动右前臂但不完成动作；
2. 观察两端状态同步变化；
3. 等待恢复 idle；
4. 不要用测试动作提前污染正式 Session。

---

## 6. 开始正式 Session

### 6.1 相机与佩戴

- MaixCAM 横放；
- 距离 1.5–2.0 m；
- 高度约为胸口；
- 右肩、右肘、右腕、右髋完整可见；
- 避免背对窗户；
- 传感器固定在右前臂背侧；
- X 轴指向手部；
- 上臂自然靠近躯干。

### 6.2 按当前模式开始 Session

#### 电脑端单独模式

1. 保持身体直立、右臂自然下垂；
2. 点击 **Recapture baseline**；
3. 点击 **Reset range**；
4. Web 输入 `Demo-01`；
5. 点击 **Start session**；
6. 保持中立姿势 1 秒再开始动作。

#### 手机端单独模式

1. iPhone 输入 `Demo-01`；
2. 确认 Required 项为 Ready；
3. 先保持身体直立、右臂自然下垂；
4. 点击 **Start Session**；
5. 在整个 3-2-1 倒计时中保持该姿势；
6. App 会自动发送 baseline 和 start 命令。

#### 电脑与手机同步模式

建议使用 iPhone 控制：

1. 输入 `Demo-01`；
2. 确认 Required 项为 Ready；
3. 点击 **Start Session**；
4. 若弹出可选设备缺失，确认情况后点击 **Start Anyway**；
5. 保持身体直立、右臂自然下垂；
6. 等待 3-2-1；
7. iPhone 会在倒计时后自动发送 baseline 和 start 命令。

电脑 Web 应自动变化：

- 顶部出现 Recording；
- Participant 变为 `Demo-01`；
- 次数从 0 开始；
- iPhone 进入 Active Training。

如果决定改用电脑控制，则先在 Web 保持中立并点击 Recapture baseline 和 Reset
range，再从 Web Start；iPhone 不再点击 Start，并会根据共享快照自动进入 Active。

若一端显示 Recording、另一端没有：

1. 不要再次点击 Start；
2. 等待 2–3 秒；
3. 检查 iPhone Wi-Fi；
4. 检查 Mac 终端是否仍运行；
5. 必要时结束当前 Session 后重新配对。

---

## 7. Demo 要做的动作

建议：3 次正常肘屈伸 + 3 次正常前臂旋转 + 1 次过快 + 1 次幅度不足 + 1 次躯干代偿。

### 7.1 正常肘部屈伸：3 次

初始姿势：

- 身体直立；
- 上臂贴近躯干；
- 右臂自然下垂；
- 手掌朝向身体；
- 不耸肩。

每次：

1. 静止 0.5 秒；
2. 用约 1 秒平稳弯曲肘部；
3. 前臂抬到约 70–100°；
4. 用约 1 秒平稳回到自然下垂；
5. 回到起点停 0.5–1 秒；
6. 再做下一次。

两端预期：

- 动作显示 `Elbow flexion`；
- 完整返回后次数增加 1；
- 接收端发出一声短高音；
- 反馈趋向 `Good form`；
- ROM 更新；
- 电脑与手机次数一致。

### 7.2 正常前臂旋转：3 次

初始姿势：

- 上臂靠近身体；
- 肘部自然微屈或保持约 90°；
- 手腕中立；
- 传感器随整段前臂旋转。

每次：

1. 掌心从朝内或朝下开始；
2. 用约 0.8–1 秒旋转到掌心朝前或朝上；
3. 用约 0.8–1 秒回到起点；
4. 停 0.5–1 秒；
5. 再做下一次。

预期：

- 动作显示 `Forearm rotation`；
- 次数增加 1；
- 一声短高音；
- 电脑和手机同步。

不要只甩手腕，也不要用肩膀带动整个手臂。

### 7.3 过快：1 次

1. 从自然下垂开始；
2. 快速完成一次弯曲和返回；
3. 总时间约 0.45 秒以内；
4. 完成后立即停止。

预期：

- OLED 显示 `FAST`；
- 只要动作幅度足够，次数会增加 1；
- 蜂鸣器静音，不播放成功音；
- 电脑和手机提示减速；
- 报告记录 `too_fast`，良好百分比下降。

不要高速冲击关节极限。

### 7.4 幅度不足：1 次

1. 从中立位置开始；
2. 只弯曲约 20–30°；
3. 返回起点；
4. 停止并等待更新。

预期：

- OLED 显示 `RANGE`；
- 次数不增加；
- 蜂鸣器静音；
- 两端提示增加活动范围。

若系统一直 idle，稍微加快小幅往返，但不要扩大到正常动作。

### 7.5 躯干代偿：1 次

1. 做一次肘部屈伸；
2. 同时让躯干向一侧倾斜约 10–15 cm；
3. 保证肩、髋仍在画面内；
4. 完成后恢复直立。

预期：

- 电脑和手机显示 `Avoid trunk compensation`；
- 这是视觉姿态提示；
- 若动作本身完整，固件会增加 1 次；
- 当前良好动作百分比主要来自固件质量，不是临床姿态评分。

按本手册完整执行时，预期最终被计数次数为 8：6 次正常动作、1 次幅度足够的
FAST、1 次完整的躯干代偿动作。RANGE 不计数。如果不是 8，先根据报告中的动作质量
和现场状态解释原因，不要把 6–8 的不确定范围写进最终结果。

### 7.6 ECG 展示

安全做法：

1. 未贴电极时展示 Leads off；
2. 按 RA、LA、RL 标签贴电极；
3. 保持静止；
4. 展示两端同步波形/BPM；
5. 说明 ECG 不参与动作识别。

不要通过剧烈运动故意触发高心率警报。`>150 BPM` 规则未经医学验证。

---

## 8. 推荐的双端同步答辩顺序

1. 指出穿戴端、接收端、MaixCAM、电脑和 iPhone；
2. 展示接收端 `BLE OK`；
3. 展示电脑与手机同一实时画面；
4. 在 iPhone 点击 Start Session；
5. 电脑自动出现 Recording；
6. 3 次正常肘屈伸；
7. 3 次正常前臂旋转；
8. 1 次过快；
9. 1 次幅度不足；
10. 1 次躯干代偿；
11. 在 iPhone 点击 Finish Session；
12. 电脑自动停止 Recording；
13. 电脑打开 History/Report；
14. iPhone 查看 Completion/History。

时间不足时保留：

- 两端同步；
- 3 次肘屈伸；
- 3 次前臂旋转；
- 1 次过快；
- 结束后的报告。

---

## 9. 结束和保存

### 9.1 按启动端结束

- 电脑端单独模式：在 Web 点击 **Stop session** 并确认；
- 手机端单独模式：在 iPhone 点击 **Finish Session** 并确认；
- 双端模式：从开始 Session 的同一端结束，另一端不要重复 Stop。

如果 iPhone 断线，可在 Web 点击 Stop session 作为恢复手段；iPhone 重连后会同步完成状态。

### 9.2 检查报告

电脑：

1. 打开 Session History；
2. 找到 `Demo-01`；
3. 打开报告。

检查：

- Repetitions；
- Counted repetition quality；
- Good form；
- Max ROM；
- Parsed IMU rows；
- Valid pose；
- ECG 状态；
- 工程原型免责声明。

iPhone：

1. 在 Completion 查看次数、ROM 和最终反馈；
2. 点击 View in History；
3. 确认与电脑是同一个 Session。

### 9.3 查找文件

```bash
ls -lt python/sessions | head
```

每次 Session 通常生成：

```text
<session-id>.csv
<session-id>_ecg.csv
```

### 9.4 停止服务

1. 确认 Session 已结束；
2. 回到 Mac 后端终端；
3. 按 `Ctrl+C`；
4. 等待程序退出；
5. MaixVision 点击 Stop；
6. 先取下 ECG 电极；
7. 再断开接收端和穿戴端。

不要在 Recording 时直接关闭终端。

---

## 10. 同步故障排查

### 10.1 iPhone 无法扫码连接

- Mac 与 iPhone 必须在同一网络；
- `MAC_IP` 不能是 `127.0.0.1`、`0.0.0.0` 或 MaixCAM IP；
- 启动参数必须包含 `--host 0.0.0.0 --mobile`；
- macOS 防火墙允许 Python；
- 旧配对先 Disconnect/Repair；
- 重启后端后重新扫新二维码。

iPhone Safari 可先测试 Mac 是否可达：

```text
http://<MAC_IP>:8000
```

若访问 `/api/mobile/health`，未带配对令牌时出现 `Pairing required` 或 HTTP 401
也说明网络已经到达 Mac，只是认证按设计生效。如果根地址完全无法打开，问题在网络或
防火墙，不在 App。

### 10.2 手机与电脑次数不同

1. 等待 1–2 秒；
2. 确认 iPhone Live connection 为 connected；
3. 确认只有一个 Mac 后端在运行；
4. 不要在两个界面同时 Start；
5. 不要打开旧二维码对应的另一个端口；
6. 仍不同则结束 Session、重启后端、重新配对。

### 10.3 一端 Recording，另一端没有

- 不要重复点击 Start；
- 检查后端终端错误；
- 等待 WebSocket 重连；
- iPhone 切换一次 Wi-Fi；
- 若 5 秒后仍不一致，从正在 Recording 的一端 Stop，再重新开始。

### 10.4 iPhone Camera unavailable，电脑有画面

- 等待 iPhone 相机请求自动重试；
- 确认 Mac 后端仍能访问 `/api/camera.jpg`；
- 检查 iPhone 到 Mac 的 Wi-Fi；
- 不需要让 iPhone 直接访问 MaixCAM；iPhone 图像来自 Mac 后端。

### 10.5 Web 串口不可用

```bash
python -m serial.tools.list_ports -v
```

- 关闭所有 Monitor；
- 按接收端 RST；
- 用准确 `$RECEIVER_PORT` 重启后端。

### 10.6 OLED 一直 BLE WAIT

1. 穿戴端断电；
2. 接收端 RST；
3. 穿戴端上电并静置 2 秒；
4. 两板靠近；
5. 仍失败则重新烧录。

### 10.7 MaixCAM 不可用

- 确认 MaixVision 仍在 Run；
- 检查 RTSP URL；
- 检查 USB NCM；
- 测试：

```bash
ping -c 3 10.203.102.1
```

RTSP 失败时的完整 UVC 备用流程：

1. MaixCAM Settings → USB Settings 中启用 UVC；
2. 将 `maixcam2/main.py` 的 `MODE` 改为 `"uvc"`；
3. 在 MaixVision 重新 Run；
4. 查找电脑相机编号：

```bash
PYTHONPATH=python python scripts/probe_cameras.py
```

5. 假设新增编号为 1，电脑端启动：

```bash
PYTHON=python ./scripts/start_web_demo.sh 1 \
  --port "$RECEIVER_PORT" \
  --side right \
  --sessions-dir python/sessions \
  --model python/models/imu_cnnbigru.pt
```

6. 手机或双端模式则把标准 `--mobile` 命令中的第一个 `"$CAMERA_RTSP"` 改成编号
`1`，其他参数保持不变。

### 10.8 8000 端口被占用

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

若是上一次 LiteRehab，在对应终端按 `Ctrl+C`。不要随意终止不认识的系统进程。

临时改端口时，后端二维码和 iPhone配对必须使用同一个新端口：

```bash
PYTHON=python ./scripts/start_web_demo.sh "$CAMERA_RTSP" \
  --host 0.0.0.0 \
  --web-port 8001 \
  --mobile \
  --advertised-host "$MAC_IP" \
  --no-browser \
  --port "$RECEIVER_PORT" \
  --side right \
  --sessions-dir python/sessions \
  --model python/models/imu_cnnbigru.pt
```

电脑打开 `http://127.0.0.1:8001`，iPhone 重新扫描新二维码。

---

## 11. 演示前检查表

### 所有模式共同检查

- [ ] 正确分支已拉取；
- [ ] Python 3.12；
- [ ] `./scripts/test_all.sh` 通过；
- [ ] 两块板已烧录；
- [ ] MaixCAM RTSP 可连接；
- [ ] 正常动作可计数和响一声；
- [ ] FAST 增加次数但不播放成功音；
- [ ] RANGE 不增加次数；
- [ ] 已录制 60–90 秒备用视频。

### 手机端或双端模式额外检查

- [ ] iPhone App 已安装；
- [ ] Mac IP 非空且是 iPhone 可访问的地址；
- [ ] iPhone 能扫描当前后端二维码；
- [ ] 手机端可以 Start/Finish；

### 双端同步模式额外检查

- [ ] 只运行一个 `--mobile` 后端；
- [ ] 电脑和手机同步显示；
- [ ] 从任一端 Finish/Stop 后，另一端同步停止 Recording；
- [ ] 两端能打开同一 Session。

### 演示前 10 分钟

- [ ] Mac 电量充足；
- [ ] 使用 ECG 时拔掉交流充电器；
- [ ] benchmark 和高负载程序已关闭；
- [ ] 所有串口 Monitor 已关闭；
- [ ] BLE OK；
- [ ] MaixVision 正在运行；
- [ ] `demo_doctor` 无 failure；
- [ ] 正式 Session 尚未开始；
- [ ] 在非 Recording 状态试做 1 次肘屈伸和 1 次前臂旋转；
- [ ] 试做结束后确认没有遗留 Recording；
- [ ] 手机/双端模式下 Mac IP 正确且 iPhone 已重新扫码；
- [ ] 双端模式下两端状态一致；
- [ ] 记得只从选定的一端 Start/Finish，另一端只观察。

---

## 12. 最短复制命令

### 烧录

```bash
cd /path/to/lite-rehab-mvp
conda activate literehab

python -m serial.tools.list_ports -v
export WEARABLE_PORT="/dev/cu.usbserialXXXX"
export RECEIVER_PORT="/dev/cu.usbmodemXXXX"

./scripts/build_all.sh
./scripts/flash_wearable.sh "$WEARABLE_PORT"
./scripts/flash_receiver.sh "$RECEIVER_PORT"
```

### 电脑端单独 Demo

```bash
cd /path/to/lite-rehab-mvp
conda activate literehab

export RECEIVER_PORT="/dev/cu.usbmodemXXXX"
export CAMERA_RTSP="rtsp://10.203.102.1:8554/live"

./scripts/demo_doctor.sh

PYTHON=python ./scripts/start_web_demo.sh "$CAMERA_RTSP" \
  --port "$RECEIVER_PORT" \
  --side right \
  --sessions-dir python/sessions \
  --model python/models/imu_cnnbigru.pt
```

### 手机端单独 Demo

```bash
cd /path/to/lite-rehab-mvp
conda activate literehab

export RECEIVER_PORT="/dev/cu.usbmodemXXXX"
export CAMERA_RTSP="rtsp://10.203.102.1:8554/live"
export MAC_IP="$(ipconfig getifaddr en0)"

if [[ -z "$MAC_IP" ]]; then
  echo "MAC_IP 为空：先执行 ipconfig getifaddr en1，或手动 export MAC_IP=真实局域网IP"
else
  ./scripts/demo_doctor.sh

  PYTHON=python ./scripts/start_web_demo.sh "$CAMERA_RTSP" \
    --host 0.0.0.0 \
    --web-port 8000 \
    --mobile \
    --advertised-host "$MAC_IP" \
    --no-browser \
    --port "$RECEIVER_PORT" \
    --side right \
    --sessions-dir python/sessions \
    --model python/models/imu_cnnbigru.pt
fi
```

随后只在 iPhone 扫描二维码和 Start/Finish，不需要打开电脑 Web。

### 电脑 + iPhone 同步 Demo

运行上面的“手机端单独 Demo”后端命令一次，然后：

```bash
open http://127.0.0.1:8000
```

再在 iPhone 扫描同一个终端二维码。不要另外运行“电脑端单独 Demo”命令。建议只在 iPhone Start/Finish，电脑 Web 负责展示。

---

LiteRehab 是课程工程原型，不用于诊断、治疗、临床评分、医学监护或替代物理治疗师。
