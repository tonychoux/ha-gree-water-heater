# HA Gree Water Heater

Home Assistant 自定义集成，用于控制 Gree 空气能热水器，支持温度调节、模式切换、传感器数据监控及热水量计算。

**项目来自** [cybaijie/ha-gree-water-heater](https://github.com/cybaijie/ha-gree-water-heater)
才疏学浅，Fork之后的修来都是来自AI
---

## ✨ 功能特性

- 🌡️ **温度控制**：35-55°C 精准目标温度调节
- 🔄 **多模式支持**：加热 / 节能 / 高需 / 关闭四种模式
- 🌡️ **多点测温**：高/中/低三位置水温传感器
- 💧 **智能计算**：实时热水量百分比（目标/实际）
- ⏰ **预约定时**：支持定时开关机设置
- 📱 **UI配置**：全图形化配置流程，无需编辑YAML
- 🏠 **设备集成**：自动识别并在Home Assistant设备面板显示

---

## 📦 安装

### 方法一：通过 HACS 安装（推荐）

1. 打开 HACS → **自定义仓库**
2. 点击 **添加自定义仓库**
3. 输入仓库地址：`https://github.com/cybaijie/ha-gree-water-heater`
4. 类别选择 **Integration**
5. 在 HACS 中搜索 **Gree Water Heater** 并安装
6. 重启 Home Assistant

### 方法二：手动安装

```bash
# 1. 进入 Home Assistant custom_components 目录
cd /config/custom_components

# 2. 下载集成
git clone https://github.com/cybaijie/ha-gree-water-heater.git
mv ha-gree-water-heater/custom_components/greeWat ./

# 3. 重启 Home Assistant
```

---

## ⚙️ 配置

### 图形化配置

1. 进入 **设置 → 设备与服务**
2. 点击 **添加集成**
3. 搜索 **Gree Water Heater**
4. 填写设备信息：
   - **名称**：自定义显示名称
   - **主机 IP**：热水器设备IP地址
   - **端口**：默认 7000
   - **MAC 地址**：设备MAC（无需冒号分隔）
   - **加密版本**：根据设备型号选 1 或 2
   - **超时时间**：默认 10 秒

---

## 📊 实体说明

集成会自动创建以下实体：

| 实体类型 | 名称 | 说明 |
|----------|------|------|
| `water_heater` | Gree Water Heater | 主控制实体 |
| `sensor` | 热水器高温值 | 顶部温度传感器 |
| `sensor` | 热水器中温值 | 中部温度传感器 |
| `sensor` | 热水器低温值 | 底部温度传感器 |
| `sensor` | 实际热水占比 | 当前可用热水百分比 |
| `sensor` | 目标热水占比 | 达到目标温度的热水量 |
<img width="532" height="537" alt="image" src="https://github.com/user-attachments/assets/e31d197a-8900-47bc-bd26-45ba3e4f7e40" />
<img width="618" height="527" alt="image" src="https://github.com/user-attachments/assets/84498efa-5abf-42ea-89f0-6227d9e8cdef" />

---

## 🔍 故障排除

### 问题1：无法连接设备
**现象**：日志显示 `Could not connect with device`

**解决**：
1. 确认设备IP地址正确且可ping通
2. 检查热水器是否开启并接入同一局域网
3. 尝试修改加密版本（1或2）
4. 在热水器面板确认已启用网络功能

### 问题2：认证失败
**现象**：日志显示 `Error getting device encryption key`

**解决**：
1. 确认MAC地址格式正确（无冒号，小写）
2. 尝试重置热水器网络设置
3. 检查路由器防火墙是否阻止UDP端口7000

### 问题3：数据不更新
**现象**：传感器状态长时间不变

**解决**：
1. 检查 `SCAN_INTERVAL` 设置（默认60秒）
2. 查看热水器是否处于关机状态
3. 检查日志是否有 `device offline` 提示

---

## 📋 更新日志

### v1.0.0
- 初始版本（基于 jamelu001/gree_water_heater）

---

## 🙏 致谢

- **原作者**：[@RobHofmann](https://github.com/RobHofmann/HomeAssistant-GreeClimateComponent) 的 HomeAssistant-GreeClimateComponent 项目
- **原作者**：[@jamelu001](https://github.com/jamelu001/gree_water_heater?tab=readme-ov-file) 的 Gree Water Heater 项目
- **加密实现**：pycryptodome 库
- **协议分析**：Gree 设备社区研究者

---

## 🔗 链接

- **GitHub 仓库**: https://github.com/cybaijie/ha-gree-water-heater
- **问题反馈**: https://github.com/cybaijie/ha-gree-water-heater/issues
- **Home Assistant 社区**: https://community.home-assistant.io

---

## 💡 贡献

欢迎提交 Issue 和 Pull Request！
