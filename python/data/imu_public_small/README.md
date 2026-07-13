# 小规模公开 IMU 训练子集

本目录不是用户自行录制的数据。它由公开数据集
“Smartwatch IMU Dataset for Upper-Limb Movement Analysis”裁剪和转换得到：

- 来源：https://doi.org/10.17632/s86tdtmcc2.1
- 作者：Yassine Benachour、Moez Rehman、Farid Flitti
- 许可证：CC BY 4.0
- 使用对象：3 位公开参与者的右腕数据
- 动作：肘屈伸、前臂旋转、肩屈伸
- 转换：100 Hz 降采样至 50 Hz，角速度由 rad/s 转换为 deg/s
- 规模：每位参与者每种动作只保留一个短片段，共 7,600 个采样点

对应转换脚本为 `python/prepare_public_imu.py`。训练生成的
`python/models/imu_cnnbigru.pt` 默认由 Dashboard 自动加载。静止状态不使用
自录训练数据，而是继续采用 ESP32 固件的 `idle` 规则门控。
