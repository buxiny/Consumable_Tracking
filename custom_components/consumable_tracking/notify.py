"""企业微信通知管理模块 / WeChat Work notification manager."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .storage import ConsumableStorage

from .const import (
    ATTR_CATEGORY,
    ATTR_DURATION_UNIT,
    ATTR_DURATION_VALUE,
    ATTR_EXPECTED_END_DATE,
    ATTR_HISTORY,
    ATTR_LAST_NOTIFIED,
    ATTR_NAME,
    ATTR_NOTE,
    ATTR_START_DATE,
    CONF_CHECK_TIME,
    CONF_DUE_NOTIFICATION,
    CONF_ENABLED,
    CONF_INTERVAL_MONTHS,
    CONF_NOTIFY_DAY,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_TIME,
    CONF_PERIODIC_SUMMARY,
    CONF_REMIND_DAYS,
    DEFAULT_CHECK_TIME,
    DEFAULT_INTERVAL_MONTHS,
    DEFAULT_NOTIFY_DAY,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_NOTIFY_TIME,
    DEFAULT_REMIND_DAYS,
)

_LOGGER = logging.getLogger(__name__)


class NotificationManager:
    """耗材通知管理调度器."""

    def __init__(
        self,
        hass: HomeAssistant,
        storage: ConsumableStorage,
        config: dict[str, Any],
    ) -> None:
        """初始化通知器."""
        self.hass = hass
        self.storage = storage
        self.config = config

        self.notify_service: str = config.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE)
        self.check_time: str = config.get(CONF_CHECK_TIME, DEFAULT_CHECK_TIME)

        due_cfg = config.get(CONF_DUE_NOTIFICATION, {})
        self.due_enabled: bool = due_cfg.get(CONF_ENABLED, True)
        self.remind_days: list[int] = due_cfg.get(CONF_REMIND_DAYS, DEFAULT_REMIND_DAYS)

        summary_cfg = config.get(CONF_PERIODIC_SUMMARY, {})
        self.summary_enabled: bool = summary_cfg.get(CONF_ENABLED, True)
        self.interval_months: int = summary_cfg.get(CONF_INTERVAL_MONTHS, DEFAULT_INTERVAL_MONTHS)
        self.notify_day: int = summary_cfg.get(CONF_NOTIFY_DAY, DEFAULT_NOTIFY_DAY)
        self.notify_time: str = summary_cfg.get(CONF_NOTIFY_TIME, DEFAULT_NOTIFY_TIME)

    async def _async_send_wework(self, title: str, message: str) -> None:
        """发送企业微信消息."""
        domain, _, service = self.notify_service.partition(".")
        if not domain or not service:
            domain = "notify"
            service = "wework"

        service_data = {
            "title": title,
            "message": message,
            "data": {
                "msgtype": "markdown",
            },
        }

        try:
            _LOGGER.info("正在发送企业微信通知 [%s]: %s", self.notify_service, title)
            await self.hass.services.async_call(
                domain,
                service,
                service_data,
                blocking=True,
            )
        except Exception as err:
            _LOGGER.error("发送企业微信通知失败 (%s): %s", self.notify_service, err)

    async def async_check_due_items(self) -> None:
        """检查并通知即将到期或已到期的耗材."""
        if not self.due_enabled:
            return

        today = date.today()
        items = self.storage.get_items()

        for item in items:
            item_id = item["id"]
            name = item.get(ATTR_NAME, "未知耗材")
            category = item.get(ATTR_CATEGORY, "未分类")
            remaining_days = item.get("remaining_days", 9999)
            last_notified: list[int] = item.get(ATTR_LAST_NOTIFIED, [])

            # 判断是否触发配置的提醒天数（如 14, 7, 0 天）
            triggered_tier = None
            for tier in sorted(self.remind_days, reverse=True):
                # 如果当前剩余天数小于等于该梯度，且该梯度未曾通知过
                if remaining_days <= tier and tier not in last_notified:
                    triggered_tier = tier
                    break

            if triggered_tier is not None:
                # 组织 Markdown 消息
                if remaining_days < 0:
                    status_desc = f"🚨 **已超期 {abs(remaining_days)} 天**"
                elif remaining_days == 0:
                    status_desc = "⚠️ **今日到期，请及时更换！**"
                else:
                    status_desc = f"⚠️ 距离预设到期还有 **{remaining_days} 天**"

                start_ym = item.get("start_ym", "")
                expected_ym = item.get("expected_ym", "")
                dur_val = item.get(ATTR_DURATION_VALUE, 12)
                dur_unit = "个月" if item.get(ATTR_DURATION_UNIT) == "month" else "天"

                # 历史对比数据提取
                history_list = item.get(ATTR_HISTORY, [])
                history_text = "暂无过往记录"
                if history_list:
                    last_h = history_list[0]
                    history_text = f"上次使用周期 {last_h.get('start_date')}~{last_h.get('end_date')} (共 {last_h.get('duration_desc')})"

                note = item.get(ATTR_NOTE) or "无"

                message = (
                    f"### 🔔【家庭耗材到期提醒】\n"
                    f"**耗材名称**：{name}\n"
                    f"**所属分类**：{category}\n"
                    f"**当前状态**：{status_desc}\n"
                    f"**开始时间**：{start_ym}\n"
                    f"**预设结束**：{expected_ym}（预设周期 {dur_val}{dur_unit}）\n"
                    f"**历史对比**：{history_text}\n"
                    f"**规格备忘**：{note}\n\n"
                    f"> 请提前选购或准备更换；更换后请进入 Home Assistant 耗材卡片点击【已更换】重置。"
                )

                title = f"耗材到期提醒: {name} (剩{remaining_days}天)" if remaining_days >= 0 else f"耗材超期预警: {name}"
                await self._async_send_wework(title, message)

                # 更新已通知梯度
                last_notified.append(triggered_tier)
                raw_item = self.storage.get_item(item_id)
                if raw_item:
                    raw_item[ATTR_LAST_NOTIFIED] = last_notified
                    await self.storage.async_save_item(raw_item)

    async def async_send_summary_report(self, force: bool = False) -> None:
        """生成并发送全量耗材季度汇总报告."""
        today = date.today()
        last_summary = self.storage.get_last_summary_date()

        if not force:
            if not self.summary_enabled:
                return
            # 检查是否满足月份间隔
            if last_summary:
                try:
                    last_dt = datetime.strptime(last_summary, "%Y-%m-%d").date()
                    # 估算月份差
                    diff_months = (today.year - last_dt.year) * 12 + (today.month - last_dt.month)
                    if diff_months < self.interval_months:
                        _LOGGER.debug("未达季度汇总通知月份间隔 (%d < %d)", diff_months, self.interval_months)
                        return
                except Exception:
                    pass

        items = self.storage.get_items()
        if not items:
            _LOGGER.info("当前无任何耗材记录，跳过汇总报告发送")
            return

        expired_items = []
        warning_items = []
        good_items = []

        for it in items:
            status = it.get("status")
            rem = it.get("remaining_days", 0)
            name = it.get(ATTR_NAME, "未知")
            dur = f"{it.get(ATTR_DURATION_VALUE)}{'个月' if it.get(ATTR_DURATION_UNIT) == 'month' else '天'}"
            prog = f"{it.get('progress', 0)}%"

            if status == "expired":
                expired_items.append(f"- **{name}**: 已超期 {abs(rem)} 天 (预设周期 {dur})")
            elif status == "warning":
                expired_desc = "今日到期" if rem == 0 else f"剩余 {rem} 天"
                warning_items.append(f"- **{name}**: {expired_desc} (进度 {prog}，周期 {dur})")
            else:
                good_items.append(f"- **{name}**: 剩余 {rem} 天 (进度 {prog})")

        lines = [
            "### 📊【家庭耗材与事务跟踪】季度使用总览",
            f"统计日期：{today.strftime('%Y-%m-%d')}\n",
        ]

        if expired_items:
            lines.append(f"🔴 **已超期 / 急需更换** ({len(expired_items)}项)")
            lines.extend(expired_items)
            lines.append("")

        if warning_items:
            lines.append(f"🟡 **近期到期预警** ({len(warning_items)}项)")
            lines.extend(warning_items)
            lines.append("")

        if good_items:
            lines.append(f"🟢 **状态良好 (持续跟踪中)** ({len(good_items)}项)")
            lines.extend(good_items[:10])  # 良好状态最多显示10条，避免超长
            if len(good_items) > 10:
                lines.append(f"- ... 及其他 {len(good_items) - 10} 项良好耗材")
            lines.append("")

        lines.append(f"> 共有 {len(items)} 项耗材与家庭维护事务在跟踪监控中。")

        title = f"耗材季度总览: {len(expired_items)}项超期, {len(warning_items)}项临期"
        await self._async_send_wework(title, "\n".join(lines))
        await self.storage.async_set_last_summary_date(today.strftime("%Y-%m-%d"))
