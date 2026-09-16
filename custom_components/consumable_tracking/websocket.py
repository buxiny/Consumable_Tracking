"""WebSocket 接口服务 / WebSocket API handlers for Consumable Tracking."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    WS_TYPE_DELETE_ITEM,
    WS_TYPE_GET_CONFIG,
    WS_TYPE_LIST_ITEMS,
    WS_TYPE_RESET_ITEM,
    WS_TYPE_SAVE_ITEM,
)

if TYPE_CHECKING:
    from .storage import ConsumableStorage

_LOGGER = logging.getLogger(__name__)


def async_register_websocket_api(hass: HomeAssistant, storage: ConsumableStorage) -> None:
    """注册 WebSocket API 处理器."""

    @websocket_api.websocket_command({
        "type": WS_TYPE_LIST_ITEMS,
    })
    @websocket_api.async_response
    async def ws_list_items(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """获取所有耗材列表."""
        items = storage.get_items()
        connection.send_result(msg["id"], items)

    @websocket_api.websocket_command({
        "type": WS_TYPE_SAVE_ITEM,
        "item": dict,
    })
    @websocket_api.async_response
    async def ws_save_item(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """新建或保存耗材."""
        item_data = msg.get("item", {})
        saved_item = await storage.async_save_item(item_data)
        connection.send_result(msg["id"], saved_item)

        # 触发状态更新事件
        hass.bus.async_fire(f"{DOMAIN}_updated", {"action": "save", "item": saved_item})

    @websocket_api.websocket_command({
        "type": WS_TYPE_DELETE_ITEM,
        "item_id": str,
    })
    @websocket_api.async_response
    async def ws_delete_item(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """删除耗材."""
        item_id = msg.get("item_id", "")
        success = await storage.async_delete_item(item_id)
        connection.send_result(msg["id"], {"success": success, "item_id": item_id})

        # 触发状态更新事件
        hass.bus.async_fire(f"{DOMAIN}_updated", {"action": "delete", "item_id": item_id})

    @websocket_api.websocket_command({
        "type": WS_TYPE_RESET_ITEM,
        "item_id": str,
        websocket_api.vol.Optional("new_start_date"): str,
        websocket_api.vol.Optional("note"): str,
    })
    @websocket_api.async_response
    async def ws_reset_item(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """更换/重置耗材."""
        item_id = msg.get("item_id", "")
        new_start_date = msg.get("new_start_date")
        note = msg.get("note", "")
        res = await storage.async_reset_item(item_id, new_start_date, note)
        connection.send_result(msg["id"], res)

        # 触发状态更新事件
        hass.bus.async_fire(f"{DOMAIN}_updated", {"action": "reset", "item": res})

    @websocket_api.websocket_command({
        "type": WS_TYPE_GET_CONFIG,
    })
    @websocket_api.async_response
    async def ws_get_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """获取当前系统与通知配置概要."""
        data = hass.data.get(DOMAIN, {})
        cfg = data.get("config", {})
        connection.send_result(
            msg["id"],
            {
                "version": "1.0.1",
                "notify_service": cfg.get("notify_service"),
                "due_notification": cfg.get("due_notification"),
                "periodic_summary": cfg.get("periodic_summary"),
            },
        )

    # 批量注册命令
    websocket_api.async_register_command(hass, ws_list_items)
    websocket_api.async_register_command(hass, ws_save_item)
    websocket_api.async_register_command(hass, ws_delete_item)
    websocket_api.async_register_command(hass, ws_reset_item)
    websocket_api.async_register_command(hass, ws_get_config)
    _LOGGER.debug("已注册 Consumable Tracking WebSocket API")
