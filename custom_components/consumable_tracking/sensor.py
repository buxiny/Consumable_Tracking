"""耗材跟踪传感器平台 / Sensor platform for Consumable Tracking."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    ATTR_CATEGORY,
    ATTR_DURATION_UNIT,
    ATTR_DURATION_VALUE,
    ATTR_EXPECTED_END_DATE,
    ATTR_HISTORY,
    ATTR_NOTE,
    ATTR_START_DATE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """初始化传感器平台."""
    data = hass.data.get(DOMAIN)
    if not data:
        return

    storage = data["storage"]
    items = storage.get_items()

    entities = [ConsumableSensor(hass, storage, item["id"]) for item in items]
    async_add_entities(entities, update_before_add=True)

    # 监听新增/删除事件
    async def handle_update(event: Any) -> None:
        action = event.data.get("action")
        if action == "save":
            item = event.data.get("item", {})
            item_id = item.get("id")
            # 查找是否已有该 entity
            existing = [e for e in entities if e.item_id == item_id]
            if not existing and item_id:
                new_ent = ConsumableSensor(hass, storage, item_id)
                entities.append(new_ent)
                async_add_entities([new_ent], update_before_add=True)
            else:
                for ent in existing:
                    ent.async_schedule_update_ha_state(force_refresh=True)
        elif action in ("reset", "delete"):
            for ent in entities:
                ent.async_schedule_update_ha_state(force_refresh=True)

    hass.bus.async_listen(f"{DOMAIN}_updated", handle_update)


class ConsumableSensor(SensorEntity):
    """单个耗材传感器实体."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, storage: Any, item_id: str) -> None:
        """初始化传感器."""
        self.hass = hass
        self._storage = storage
        self.item_id = item_id
        self._attr_unique_id = f"consumable_{item_id}"
        self.entity_id = f"sensor.consumable_{item_id}"

    @property
    def item_data(self) -> dict[str, Any]:
        """获取最新耗材数据."""
        return self._storage.get_item(self.item_id) or {}

    @property
    def name(self) -> str:
        """实体名称."""
        return self.item_data.get("name", f"耗材 {self.item_id}")

    @property
    def icon(self) -> str:
        """实体图标."""
        return self.item_data.get("icon", "mdi:package-variant")

    @property
    def native_value(self) -> int:
        """状态值：剩余天数."""
        return self.item_data.get("remaining_days", 0)

    @property
    def native_unit_of_measurement(self) -> str:
        """单位：天."""
        return "天"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """扩展属性."""
        item = self.item_data
        return {
            "item_id": self.item_id,
            "category": item.get(ATTR_CATEGORY),
            "start_date": item.get(ATTR_START_DATE),
            "start_ym": item.get("start_ym"),
            "expected_end_date": item.get(ATTR_EXPECTED_END_DATE),
            "expected_ym": item.get("expected_ym"),
            "duration_value": item.get(ATTR_DURATION_VALUE),
            "duration_unit": item.get(ATTR_DURATION_UNIT),
            "progress": item.get("progress"),
            "status": item.get("status"),
            "note": item.get(ATTR_NOTE),
            "history": item.get(ATTR_HISTORY, []),
        }

    @property
    def available(self) -> bool:
        """是否有效."""
        return bool(self._storage.get_item(self.item_id))
