# Consumable Tracking (耗材与事务跟踪)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/buxiny/Consumable_Tracking?color=blue)](https://github.com/buxiny/Consumable_Tracking/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.8%2B-blue.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

适用于 **Home Assistant** 的现代、紧凑、简约家庭耗材与周期性事务跟踪集成插件。  
用于实时跟踪净水器滤芯、新风滤网、扫地机配件、各种无线设备电池（门锁/传感器/无线开关）以及家庭定期维护（如定期疏浚下水道、空调清洗等）的使用进度，并通过企业微信进行到期与定期汇总提醒。

---

## ✨ 核心特性

1. **页面便捷新建与管理**：
   - 专为 Home Assistant 定制的现代紧凑型 Lovelace 仪表盘卡片。
   - 内置快捷模板（净水器滤芯、新风滤网、扫地机耗材、门锁电池、疏浚下水道），一键预填。
   - 支持自定义分类、MDI 图标、预设周期（月/天/年）与规格备忘。
   - 支持直接在卡片上**编辑、删除**与**一键重置/更换完成**。

2. **直观现代的进度与历史对比**：
   - 显示开始与预设结束的年月（如 `2025/05 ~ 2026/05`）。
   - 极简平滑的色彩动态进度条：正常期（绿色）、临界到期（橙黄色）、超期（红色）。
   - **完成记录历史对比**：更换后自动归档上一周期，在卡片底部以小字优雅显示最新的 **2~3 条历史记录**，单行展示不占空间，方便直观对比耗材的真实使用寿命：
     > `历史: 1. 2025/05~2026/04 (12个月)  2. 2024/05~2025/05 (12个月)`

3. **深度集成企业微信通知**：
   - 完美对接已配置的 [dscao/wework_notify](https://github.com/dscao/wework_notify) 企业微信通知服务（默认 `notify.wework`）。
   - **到期自动预警**：默认在单个耗材到期前 **2 周 (14天)**、**1 周 (7天)** 以及 **到期当天** 发送排版精美的 Markdown 图文提醒（内置防重复发送机制）。
   - **定期全量汇总报告**：默认**每隔 3 个月**（季度初）自动汇总全家耗材与维护事务的运行状况，列出已超期、临期与状态良好的统计清单。
   - 全部通知规则均可在 `configuration.yaml` 中自由定制或一键开关。

4. **实体与自动化无缝集成**：
   - 为每个耗材自动生成 `sensor.consumable_<id>` 实体，状态值为“剩余天数”，属性完整包含进度百分比、历史记录与规格等，方便调用原生 HA 自动化。

---

## 🛠️ 安装与配置

### 兼容环境
- **Home Assistant Core**：2026.8.3 或更高版本
- **Home Assistant Supervisor**：2026.09.0 或更高版本
- **Home Assistant Operating System**：18.2 或更高版本

---

### 方法一：通过 HACS 安装（推荐）

1. 打开 Home Assistant 的 **HACS** 页面。
2. 点击右上角菜单，选择 **自定义存储库 (Custom repositories)**。
3. 输入仓库地址：`https://github.com/buxiny/Consumable_Tracking`，类别选择 **Integration (集成)**，点击添加。
4. 在 HACS 列表中搜索 **Consumable Tracking** 并点击下载安装。
5. 重启 Home Assistant。

---

### 方法二：手动安装

1. 下载或克隆本仓库：
   ```bash
   git clone https://github.com/buxiny/Consumable_Tracking.git
   ```
2. 将仓库中的 `custom_components/consumable_tracking` 文件夹复制到 Home Assistant 配置目录下的 `custom_components/` 目录中：
   ```
   config/
   └── custom_components/
       └── consumable_tracking/
           ├── __init__.py
           ├── const.py
           ├── manifest.json
           ├── notify.py
           ├── sensor.py
           ├── storage.py
           ├── services.yaml
           ├── strings.json
           ├── websocket.py
           └── consumable-tracking-card.js
   ```
3. 重启 Home Assistant。

---

## ⚙️ 配置文件说明 (`configuration.yaml`)

在 Home Assistant 的 `configuration.yaml` 中添加以下配置项：

```yaml
consumable_tracking:
  # 企业微信通知服务名（对接 dscao/wework_notify，默认 notify.wework）
  notify_service: notify.wework

  # 每日到期巡检时间（默认每天上午 09:30）
  check_time: "09:30:00"

  # 1. 单个耗材到期提醒设置
  due_notification:
    enabled: true
    # 默认提前 14天(2周)、7天(1周)、0天(当天) 发送提醒
    remind_days:
      - 14
      - 7
      - 0

  # 2. 定期全量汇总报告设置
  periodic_summary:
    enabled: true
    interval_months: 3       # 汇总报告推送间隔（默认每3个月）
    notify_day: 1            # 每季度首月 1 号推送
    notify_time: "10:00:00"  # 推送具体时间
```

> **注意**：如果无需修改默认参数，仅在 `configuration.yaml` 中写入 `consumable_tracking:` 即可启用全部开箱即用默认值。

---

## 📱 仪表盘卡片配置 (Lovelace Card)

本插件内置了自研的 **`consumable-tracking-card`**，集成启动时会自动托管前端资源。

### 添加到 Lovelace 仪表盘

1. 进入 Home Assistant 仪表盘，点击右上角 **编辑仪表盘** -> **添加卡片**。
2. 划到最底部选择 **手动配置 (Manual)**，输入以下代码：

```yaml
type: custom:consumable-tracking-card
title: 家庭耗材与事务跟踪
show_add: true
```

### 卡片配置参数

| 参数名 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `type` | string | `custom:consumable-tracking-card` | **必填**，自定义卡片类型 |
| `title` | string | `家庭耗材与事务跟踪` | 卡片顶部显示的标题 |
| `show_add` | boolean | `true` | 是否在卡片右上角显示“新建耗材”按钮 |
| `filter_category` | string | `null` | 可选，只显示指定分类（如 `滤芯` 或 `电池`） |

> **手动添加资源提示**（如遇某些版本未自动引入）：  
> 在 **设置** -> **控制面板** -> **资源 (Resources)** 中添加 URL：`/consumable_tracking/consumable-tracking-card.js`，资源类型选择 `JavaScript 模块`。

---

## 🛎️ 企业微信通知效果预览

### 1. 单个耗材到期提醒（提前14天/7天/当天）
```markdown
### 🔔【家庭耗材到期提醒】
**耗材名称**：净水器RO反渗透滤芯
**所属分类**：滤芯
**当前状态**：⚠️ 距离预设到期还有 7 天
**开始时间**：2025/05
**预设结束**：2026/05（预设周期 12个月）
**历史对比**：上次使用周期 2024/05~2025/05 (共 12个月)
**规格备忘**：400G大通量通用规格

> 请提前选购或准备更换；更换后请进入 Home Assistant 耗材卡片点击【已更换】重置。
```

### 2. 季度全量耗材使用总览报告（每3个月）
```markdown
### 📊【家庭耗材与事务跟踪】季度使用总览
统计日期：2026-09-01

🔴 **已超期 / 急需更换** (1项)
- 主卫下水道疏浚: 已超期 5 天 (预设周期 6个月)

🟡 **近期到期预警** (2项)
- 智能门锁电池: 剩余 7 天 (进度 98.1%，周期 12个月)
- 净水器复合滤芯: 剩余 14 天 (进度 92.3%，周期 6个月)

🟢 **状态良好 (持续跟踪中)** (4项)
- 扫地机尘袋: 剩余 45 天 (进度 50.0%)
- 新风初效滤网: 剩余 72 天 (进度 20.0%)
- 客厅人体感应器电池: 剩余 310 天 (进度 15.0%)

> 共有 7 项耗材与家庭维护事务在跟踪监控中。
```

---

## 🔧 服务调用 (Services)

插件提供了原生 Home Assistant 服务，可在 **开发者工具** -> **服务** 或原生自动化中直接调用：

- **`consumable_tracking.add_item`**：添加新的耗材/事务项。
- **`consumable_tracking.update_item`**：更新已存在的耗材参数。
- **`consumable_tracking.delete_item`**：删除指定的耗材项。
- **`consumable_tracking.reset_item`**：重置耗材（当前周期归档至历史，开启新周期）。
- **`consumable_tracking.trigger_check`**：手动立即触发一次到期状态巡检与通知。
- **`consumable_tracking.send_summary`**：手动立即向企业微信发送全量耗材季度汇总报告（参数 `force: true`）。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。
