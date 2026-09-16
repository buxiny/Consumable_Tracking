"""耗材与事务跟踪数据存储管理 / Storage manager for Consumable Tracking."""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    ATTR_CATEGORY,
    ATTR_DURATION_UNIT,
    ATTR_DURATION_VALUE,
    ATTR_EXPECTED_END_DATE,
    ATTR_HISTORY,
    ATTR_ICON,
    ATTR_ITEM_ID,
    ATTR_LAST_NOTIFIED,
    ATTR_NAME,
    ATTR_NOTE,
    ATTR_START_DATE,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


def calculate_expected_end_date(start_date_str: str, duration_val: int, duration_unit: str = "month") -> str:
    """根据开始日期与周期推算预设结束日期 (YYYY-MM-DD)."""
    try:
        if len(start_date_str) == 7:  # YYYY-MM
            start_dt = datetime.strptime(start_date_str, "%Y-%m").date()
        else:
            start_dt = datetime.strptime(start_date_str[:10], "%Y-%m-%d").date()
    except Exception:
        start_dt = date.today()

    duration_val = int(duration_val) if duration_val else 1
    if duration_unit == "day":
        end_dt = start_dt + timedelta(days=duration_val)
    elif duration_unit == "year":
        try:
            end_dt = start_dt.replace(year=start_dt.year + duration_val)
        except ValueError:
            end_dt = start_dt + timedelta(days=int(duration_val * 365.25))
    else:  # 默认为 month (按月推算)
        year_offset = (start_dt.month + duration_val - 1) // 12
        new_month = (start_dt.month + duration_val - 1) % 12 + 1
        day = min(start_dt.day, 28)
        end_dt = date(start_dt.year + year_offset, new_month, day)

    return end_dt.strftime("%Y-%m-%d")


def compute_item_metrics(item: dict[str, Any]) -> dict[str, Any]:
    """计算单个耗材的运行进度、剩余天数及状态."""
    today = date.today()
    start_date_str = item.get(ATTR_START_DATE, today.strftime("%Y-%m-%d"))
    expected_end_str = item.get(ATTR_EXPECTED_END_DATE)

    if not expected_end_str:
        expected_end_str = calculate_expected_end_date(
            start_date_str,
            item.get(ATTR_DURATION_VALUE, 12),
            item.get(ATTR_DURATION_UNIT, "month"),
        )

    try:
        start_dt = datetime.strptime(start_date_str[:10], "%Y-%m-%d").date()
    except Exception:
        start_dt = today

    try:
        end_dt = datetime.strptime(expected_end_str[:10], "%Y-%m-%d").date()
    except Exception:
        end_dt = today + timedelta(days=365)

    total_days = max((end_dt - start_dt).days, 1)
    passed_days = (today - start_dt).days
    remaining_days = (end_dt - today).days

    if passed_days < 0:
        progress = 0.0
    else:
        progress = min(round((passed_days / total_days) * 100, 1), 100.0)

    if remaining_days < 0:
        status = "expired"  # 已超期
    elif remaining_days <= 14:
        status = "warning"  # 即将到期 (<= 14 天)
    else:
        status = "good"  # 状态良好

    # 规范年月展示，例如 2025/05
    start_ym = start_dt.strftime("%Y/%m")
    expected_ym = end_dt.strftime("%Y/%m")

    return {
        "start_ym": start_ym,
        "expected_ym": expected_ym,
        "total_days": total_days,
        "passed_days": passed_days,
        "remaining_days": remaining_days,
        "progress": progress,
        "status": status,
    }


class ConsumableStorage:
    """耗材与事务数据持久化存储中心."""

    def __init__(self, hass: HomeAssistant) -> None:
        """初始化存储."""
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._items: dict[str, dict[str, Any]] = {}
        self._last_summary_date: str | None = None

    async def async_load(self) -> None:
        """从 HA Storage 加载数据."""
        data = await self._store.async_load()
        if data and isinstance(data, dict):
            raw_items = data.get("items", {})
            self._last_summary_date = data.get("last_summary_date")
            if isinstance(raw_items, dict):
                self._items = raw_items
            elif isinstance(raw_items, list):
                # 兼容列表格式
                self._items = {it.get("id"): it for it in raw_items if it.get("id")}
        else:
            self._items = {}
            self._last_summary_date = None

        _LOGGER.info("已加载 %d 项耗材与事务记录", len(self._items))

    async def async_save(self) -> None:
        """持久化数据到文件."""
        data = {
            "items": self._items,
            "last_summary_date": self._last_summary_date,
        }
        await self._store.async_save(data)

    def get_items(self) -> list[dict[str, Any]]:
        """获取所有耗材数据 (按创建/状态排序，附带动态计算指标)."""
        result = []
        for item_id, it in self._items.items():
            item_copy = dict(it)
            item_copy["id"] = item_id
            metrics = compute_item_metrics(item_copy)
            item_copy.update(metrics)
            result.append(item_copy)
        # 按剩余天数升序排列，越紧急的排在越前面
        result.sort(key=lambda x: x.get("remaining_days", 9999))
        return result

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        """获取单个耗材."""
        it = self._items.get(item_id)
        if not it:
            return None
        res = dict(it)
        res["id"] = item_id
        res.update(compute_item_metrics(res))
        return res

    async def async_save_item(self, data: dict[str, Any]) -> dict[str, Any]:
        """新建或更新耗材/事务."""
        item_id = data.get("id") or str(uuid.uuid4())[:8]

        start_date = data.get(ATTR_START_DATE)
        if not start_date:
            start_date = date.today().strftime("%Y-%m-%d")
        elif len(start_date) == 7:  # YYYY-MM
            start_date = f"{start_date}-01"

        duration_value = int(data.get(ATTR_DURATION_VALUE, 12))
        duration_unit = data.get(ATTR_DURATION_UNIT, "month")
        expected_end_date = data.get(ATTR_EXPECTED_END_DATE) or calculate_expected_end_date(
            start_date, duration_value, duration_unit
        )

        existing = self._items.get(item_id, {})
        history = data.get(ATTR_HISTORY, existing.get(ATTR_HISTORY, []))
        last_notified = data.get(ATTR_LAST_NOTIFIED, existing.get(ATTR_LAST_NOTIFIED, []))

        item_record = {
            "id": item_id,
            ATTR_NAME: str(data.get(ATTR_NAME, "未命名耗材")).strip(),
            ATTR_CATEGORY: str(data.get(ATTR_CATEGORY, "通用")).strip(),
            ATTR_ICON: str(data.get(ATTR_ICON, "mdi:package-variant")).strip(),
            ATTR_START_DATE: start_date,
            ATTR_DURATION_VALUE: duration_value,
            ATTR_DURATION_UNIT: duration_unit,
            ATTR_EXPECTED_END_DATE: expected_end_date,
            ATTR_NOTE: str(data.get(ATTR_NOTE, "")).strip(),
            ATTR_HISTORY: history[:5],  # 最多保留最新 5 条完整历史
            ATTR_LAST_NOTIFIED: last_notified,
            "updated_at": datetime.now().isoformat(),
        }

        self._items[item_id] = item_record
        await self.async_save()
        _LOGGER.debug("保存耗材记录: %s (%s)", item_record[ATTR_NAME], item_id)
        return self.get_item(item_id) or item_record

    async def async_delete_item(self, item_id: str) -> bool:
        """删除耗材/事务."""
        if item_id in self._items:
            del self._items[item_id]
            await self.async_save()
            _LOGGER.info("删除耗材记录: %s", item_id)
            return True
        return False

    async def async_reset_item(
        self,
        item_id: str,
        new_start_date: str | None = None,
        completion_note: str = "",
    ) -> dict[str, Any] | None:
        """更换/重置耗材：将当前周期归档至历史记录，开启新周期."""
        item = self._items.get(item_id)
        if not item:
            return None

        today = date.today()
        # 1. 归档当前周期进入 history
        old_start_str = item.get(ATTR_START_DATE, today.strftime("%Y-%m-%d"))
        try:
            old_start_dt = datetime.strptime(old_start_str[:10], "%Y-%m-%d").date()
        except Exception:
            old_start_dt = today

        old_start_ym = old_start_dt.strftime("%Y/%m")
        old_end_ym = today.strftime("%Y/%m")

        # 计算实际使用时长描述 (多少个月或天)
        days_used = max((today - old_start_dt).days, 1)
        if days_used >= 30:
            months = round(days_used / 30.4375)
            duration_desc = f"{months}个月"
        else:
            duration_desc = f"{days_used}天"

        history_entry = {
            "start_date": old_start_ym,
            "end_date": old_end_ym,
            "duration_desc": duration_desc,
            "days_used": days_used,
            "completed_at": today.strftime("%Y-%m-%d"),
            "note": completion_note or item.get(ATTR_NOTE, ""),
        }

        history_list = item.get(ATTR_HISTORY, [])
        # 插入到最前面
        history_list.insert(0, history_entry)
        item[ATTR_HISTORY] = history_list[:5]  # 保留最新5条

        # 2. 开启新周期
        if new_start_date:
            if len(new_start_date) == 7:
                new_start_date = f"{new_start_date}-01"
            item[ATTR_START_DATE] = new_start_date
        else:
            item[ATTR_START_DATE] = today.strftime("%Y-%m-%d")

        dur_val = item.get(ATTR_DURATION_VALUE, 12)
        dur_unit = item.get(ATTR_DURATION_UNIT, "month")
        item[ATTR_EXPECTED_END_DATE] = calculate_expected_end_date(
            item[ATTR_START_DATE], dur_val, dur_unit
        )
        # 清空当前周期的已通知记录
        item[ATTR_LAST_NOTIFIED] = []
        item["updated_at"] = datetime.now().isoformat()

        self._items[item_id] = item
        await self.async_save()
        _LOGGER.info("耗材 %s 完成重置并归档历史", item.get(ATTR_NAME))
        return self.get_item(item_id)

    def get_last_summary_date(self) -> str | None:
        """获取上次发送季度汇总报告的日期."""
        return self._last_summary_date

    async def async_set_last_summary_date(self, val: str) -> None:
        """设置上次汇总报告日期."""
        self._last_summary_date = val
        await self.async_save()
