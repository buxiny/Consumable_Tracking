"""Notification helper for Consumable Tracking (WeWork Notify Integration)."""
from __future__ import annotations

from datetime import datetime, date
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from .const import (
    CONF_CHECK_TIME,
    CONF_DUE_NOTIFICATION,
    CONF_NOTIFY_SERVICE,
    CONF_PERIODIC_SUMMARY,
    DEFAULT_CHECK_TIME,
    DEFAULT_DUE_REMIND_DAYS,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_PERIODIC_MONTHS,
    DEFAULT_PERIODIC_NOTIFY_DAY,
    DEFAULT_PERIODIC_NOTIFY_TIME,
)

if TYPE_CHECKING:
    from .storage import ConsumableStorage

_LOGGER = logging.getLogger(__name__)


class NotificationManager:
    """管理耗材的到期提醒与定期全量汇总推送."""

    def __init__(
        self,
        hass: HomeAssistant,
        storage: ConsumableStorage,
        config: dict[str, Any],
    ) -> None:
        self.hass = hass
        self.storage = storage
        self.config = config

        self.notify_service: str = config.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE)
        self.check_time: str = config.get(CONF_CHECK_TIME, DEFAULT_CHECK_TIME)

        due_cfg = config.get(CONF_DUE_NOTIFICATION, {})
        self.due_enabled: bool = due_cfg.get("enabled", True)
        self.remind_days: list[int] = due_cfg.get("remind_days", DEFAULT_DUE_REMIND_DAYS)

        summary_cfg = config.get(CONF_PERIODIC_SUMMARY, {})
        self.summary_enabled: bool = summary_cfg.get("enabled", True)
        self.summary_months: int = summary_cfg.get("interval_months", DEFAULT_PERIODIC_MONTHS)
        self.summary_day: int = summary_cfg.get("notify_day", DEFAULT_PERIODIC_NOTIFY_DAY)
        self.summary_time: str = summary_cfg.get("notify_time", DEFAULT_PERIODIC_NOTIFY_TIME)

    async def _async_send_wework(self, title: str, message: str) -> dict[str, Any]:
        """调用企业微信通知服务 (兼容 dscao/wework_notify)."""
        if not self.notify_service:
            _LOGGER.warning("未配置通知服务 (notify_service)，跳过推送")
            return {"success": False, "error": "未配置通知服务 (notify_service)"}

        # 智能解析服务 domain 与 service 名称
        svc_parts = self.notify_service.split(".", 1)
        if len(svc_parts) == 2:
            domain, service = svc_parts[0], svc_parts[1]
        else:
            domain, service = "notify", self.notify_service

        # 检查服务是否存在
        if not self.hass.services.has_service(domain, service):
            msg = f"Home Assistant 中未找到通知服务: {domain}.{service}，请确认 configuration.yaml 中的 notify 配置"
            _LOGGER.error(msg)
            return {"success": False, "error": msg}

        # dscao/wework_notify 规范：
        # msgtype 推荐 textcard 或 text (兼容性最好，绝大多数版本均完美支持)
        clean_text = message.replace("#", "").replace("**", "").replace("> ", "").strip()
        card_desc = clean_text[:512]

        service_data = {
            "title": title,
            "message": message,
            "data": {
                "msgtype": "textcard",
                "textcard": {
                    "title": title,
                    "description": card_desc,
                    "url": "https://work.weixin.qq.com",
                    "btntxt": "查看详情",
                },
            },
        }

        try:
            _LOGGER.info("正在发送企业微信通知至 %s.%s: %s", domain, service, title)
            await self.hass.services.async_call(
                domain,
                service,
                service_data,
                blocking=True,
            )
            _LOGGER.info("企业微信通知发送成功: %s", title)
            return {"success": True}
        except Exception as err:
            _LOGGER.warning("以 textcard 发送企业微信通知失败 (%s)，尝试以纯文本降级发送...", err)
            try:
                # 降级尝试普通纯文本格式
                await self.hass.services.async_call(
                    domain,
                    service,
                    {"title": title, "message": f"{title}\n\n{clean_text}"},
                    blocking=True,
                )
                _LOGGER.info("以纯文本降级发送企业微信通知成功: %s", title)
                return {"success": True}
            except Exception as fallback_err:
                _LOGGER.error("发送企业微信通知彻底失败: %s", fallback_err)
                return {"success": False, "error": str(fallback_err)}

    async def async_check_due_items(self) -> None:
        """检查单个耗材的到期状态，发送到期预警."""
        if not self.due_enabled:
            return

        items = self.storage.get_items()
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")

        for item in items:
            rem_days = item.get("remaining_days")
            if rem_days is None:
                continue

            # 判断是否命中预警阶梯天数
            matched_step = None
            if rem_days in self.remind_days:
                matched_step = rem_days
            elif rem_days < 0 and -rem_days in self.remind_days:
                matched_step = rem_days

            if matched_step is None:
                continue

            step_key = str(matched_step)
            last_notified = item.get("last_notified", {})
            if last_notified.get(step_key) == today_str:
                continue

            # 构建消息
            name = item.get("name", "未命名耗材")
            category = item.get("category", "日常")
            start = item.get("start_date", "")
            exp_end = item.get("expected_end_date", "")
            cycle = f"{item.get('duration_value', 12)}个{item.get('duration_unit', '月')}"
            note = item.get("note", "无")

            hist = item.get("history", [])
            last_hist_str = "无"
            if hist:
                h = hist[0]
                last_hist_str = f"{h.get('start_date', '')}~{h.get('end_date', '')} (实际用{h.get('duration_desc', '')})"

            if rem_days > 0:
                status_text = f"⚠️ 距离预设到期还有 {rem_days} 天"
                title = f"🔔【耗材到期预警】{name} 即将到期"
            elif rem_days == 0:
                status_text = "🚨 今日正式到期，请及时更换！"
                title = f"🚨【耗材到期提醒】{name} 今日到期"
            else:
                status_text = f"❌ 已超期 {-rem_days} 天，请尽快维护！"
                title = f"❌【耗材超期提醒】{name} 已超期"

            msg_lines = [
                f"【耗材名称】：{name}",
                f"【所属分类】：{category}",
                f"【当前状态】：{status_text}",
                f"【启用时间】：{start}",
                f"【预设到期】：{exp_end} (周期 {cycle})",
                f"【上期历史】：{last_hist_str}",
                f"【规格备忘】：{note}",
                "提示：更换后请在 Home Assistant 卡片中点击【已更换】重置周期。",
            ]
            message = "\n".join(msg_lines)

            result = await self._async_send_wework(title, message)
            if result.get("success"):
                last_notified[step_key] = today_str
                await self.storage.async_save_item({
                    "id": item["id"],
                    "last_notified": last_notified,
                })

    async def async_send_summary_report(self, force: bool = False) -> dict[str, Any]:
        """生成全量耗材使用总览报告并推送到企业微信."""
        items = self.storage.get_items()
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")

        total_count = len(items)
        if total_count == 0 and not force:
            return {"success": True, "message": "暂无耗材"}

        overdue_items = []
        warning_items = []
        normal_items = []

        for it in items:
            rem = it.get("remaining_days", 9999)
            name = it.get("name", "未命名")
            prog = it.get("progress_pct", 0)
            cycle = f"{it.get('duration_value', 12)}个{it.get('duration_unit', '月')}"

            if rem < 0:
                overdue_items.append(f"• {name}: 已超期 {-rem} 天 (预设 {cycle})")
            elif rem <= 30:
                warning_items.append(f"• {name}: 剩余 {rem} 天 (进度 {prog}%)")
            else:
                normal_items.append(f"• {name}: 剩余 {rem} 天 (进度 {prog}%)")

        title = "📊【家庭耗材与事务】使用总览报告"
        lines = [
            f"统计时间：{today_str}",
            f"跟踪总数：共 {total_count} 项",
            "",
        ]

        if overdue_items:
            lines.append(f"🔴 已超期/急需更换 ({len(overdue_items)}项):")
            lines.extend(overdue_items)
            lines.append("")

        if warning_items:
            lines.append(f"🟡 近期即将到期 ({len(warning_items)}项):")
            lines.extend(warning_items)
            lines.append("")

        if normal_items:
            lines.append(f"🟢 运行状态良好 ({len(normal_items)}项):")
            lines.extend(normal_items)
            lines.append("")

        lines.append("打开 Home Assistant 耗材跟踪卡片即可快速重置或调整。")
        message = "\n".join(lines)

        return await self._async_send_wework(title, message)
