# HA Gree Water Heater

Home assistant本地控制格力（Gree）空气能热水器。支持开关、模式、水温调节、定时预约与状态监测。

本人才疏学浅，Fork 之后的修改均来自 AI。

本集成测试机型型号ID为910001。如希望兼容更多格力型号的热水器，欢迎issue提出共建。

---

## ✨ 功能特性

- 🔄 **运行模式**：标准 / 节能 / 快速 三种模式
- 🌡️ **水温控制**：35–55°C 目标温度调节
- 📟 **状态监测**：热水水温、热水量、运行状态
- ⏰ **定时预约**：定时开关 + 可调整的开始 / 结束时间
- 📱 **图形化配置**：全程 UI 配置，无需编辑 YAML

---

## 📦 安装

### 方法一：通过 HACS 安装（推荐）

1. 打开 HACS → **自定义仓库**
2. 点击 **添加自定义仓库**
3. 输入仓库地址：`https://github.com/tonychoux/ha-gree-water-heater`
4. 类别选择 **Integration**
5. 在 HACS 中搜索 **Gree Water Heater** 并安装
6. 重启 Home Assistant > 若 HACS 更新报 domain 相关错误，先删除 HA 配置目录下残留的旧 `custom_components/greeWat/`

### 方法二：手动安装

```bash
# 1. 进入 Home Assistant custom_components 目录
cd /config/custom_components

# 2. 下载集成
git clone https://github.com/tonychoux/ha-gree-water-heater.git
mv ha-gree-water-heater/custom_components/gree_water_heater ./

# 3. 重启 Home Assistant
```

---

## ⚙️ 配置

1. 进入 **设置 → 设备与服务**
2. 点击 **添加集成**
3. 搜索 **Gree Water Heater**
4. 填写设备信息：

| 配置项    | 说明            | 默认值                |
| ------ | ------------- | ------------------ |
| 名称     | 集成显示名称        | `Gree WaterHeater` |
| 主机 IP  | 热水器 IP 地址     | 必填                 |
| 端口     | 设备 UDP 端口     | `7000`             |
| MAC 地址 | 设备 MAC（无冒号分隔） | 必填                 |
| 加密版本   | 按设备型号选择 1 或 2 | `1`                |
| 超时时间   | 请求超时（秒）       | `10`               |

> 修改设备 IP / MAC / 加密方式等，可在集成条目里通过「选项」重新配置。

---

## 📊 实体说明

集成会自动创建以下实体（均归属同一台设备，唯一 ID 基于设备 MAC）：

### 主控制实体 `water_heater`

| 能力   | 对应字段        | 说明                                                      |
| ---- | ----------- | ------------------------------------------------------- |
| 开关   | `Pow`       | 开机 / 关机                                                 |
| 运行模式 | `Wmod`      | `heat_pump` 标准 / `eco` 节能 / `high_demand` 快速 / `off` 关闭 |
| 当前水温 | `WatTmp`    |                                                         |
| 目标水温 | `SetTemInt` |                                                         |

主实体还带有「温度单位」「设备名」等状态属性。

### 传感器 `sensor`

| 实体    | 对应字段         | 说明            |
| ----- | ------------ | ------------- |
| 可用热水量 | `Watpercent` | 设备值减 100，单位 % |

### 二元传感器 `binary_sensor`

| 实体   | 对应字段     | device class | 说明                           |
| ---- | -------- | ------------ | ---------------------------- |
| 运行状态 | `Wstate` | `running`    | on = 正在加热，off = 未运行 / 保温中    |
| 整机故障 | `AllErr` | `problem`    | on = 有故障，off = 正常；原始故障码见状态属性 |

### 定时开关 `switch`

| 实体     | 对应字段   | 说明           |
| ------ | ------ | ------------ |
| 定时组1开关 | `Sch1` | 开启 / 关闭定时组 1 |
| 定时组2开关 | `Sch2` | 开启 / 关闭定时组 2 |

### 定时时间 `time`

| 实体      | 对应字段                             |
| ------- | -------------------------------- |
| 定时1开始时间 | `Wtmr1StartHr` + `Wtmr1StartMin` |
| 定时1结束时间 | `Wtmr1EndHr` + `Wtmr1EndMin`     |
| 定时2开始时间 | `Wtmr2StartHr` + `Wtmr2StartMin` |
| 定时2结束时间 | `Wtmr2EndHr` + `Wtmr2EndMin`     |

### 定时模式 `select`

| 实体   | 对应字段      | 选项                    |
| ---- | --------- | --------------------- |
| 定时模式 | `WschTyp` | `定时开关`(0) / `定时用水`(1) |

### 时间实体的可用性规则

为避免展示不生效的时间，以下情况对应时间实体会显示为「不可用」：

- 定时组开关关闭（`Sch`=0）→ 该组开始 / 结束时间不可用
- 定时模式为「定时用水」（`WschTyp`=1）→ 两个结束时间不可用（该模式下设备忽略结束时间）

---

## 🙏 致谢

- **项目修改自** [cybaijie/ha-gree-water-heater](https://github.com/cybaijie/ha-gree-water-heater)

---
