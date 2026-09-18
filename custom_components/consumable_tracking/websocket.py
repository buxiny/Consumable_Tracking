"""WebSocket API for Consumable Tracking."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    WS_TYPE_DELETE_ITEM,
    WS_TYPE_GET_CONFIG,
    WS_TYPE_LIST_ITEMS,
    WS_TYPE_REORDER_ITEMS,
    WS_TYPE_RESET_ITEM,
    WS_TYPE_SAVE_ITEM,
    WS_TYPE_SEND_SUMMARY,
)

if TYPE_CHECKING:
    from .notify import NotificationManager
    from .storage import ConsumableStorage

_LOGGER = logging.getLogger(__name__)


def async_register_websocket_api(
    hass: HomeAssistant,
    storage: ConsumableStorage,
    notify_mgr: NotificationManager | None = None,
) -> None:
    """注册 Consumable Tracking 的所有前端 WebSocket 命令."""

    @websocket_api.websocket_command({
        vol.Required("type"): WS_TYPE_LIST_ITEMS,
    })
    @websocket_api.async_response
    async def ws_list_items(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        items = storage.get_items()
        connection.send_result(msg["id"], items)

    @websocket_api.websocket_command({
        vol.Required("type"): WS_TYPE_SAVE_ITEM,
        vol.Required("item"): dict,
    })
    @websocket_api.async_response
    async def ws_save_item(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        item_data = msg["item"]
        saved_item = await storage.async_save_item(item_data)
        connection.send_result(msg["id"], saved_item)

    @websocket_api.websocket_command({
        vol.Required("type"): WS_TYPE_DELETE_ITEM,
        vol.Required("item_id"): str,
    })
    @websocket_api.async_response
    async def ws_delete_item(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        item_id = msg["item_id"]
        success = await storage.async_delete_item(item_id)
        connection.send_result(msg["id"], {"success": success, "item_id": item_id})

    @websocket_api.websocket_command({
        vol.Required("type"): WS_TYPE_RESET_ITEM,
        vol.Required("item_id"): str,
        vol.Optional("new_start_date"): str,
        vol.Optional("note"): str,
    })
    @websocket_api.async_response
    async def ws_reset_item(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        item_id = msg["item_id"]
        new_start = msg.get("new_start_date")
        note = msg.get("note")
        updated_item = await storage.async_reset_item(item_id, new_start, note)
        connection.send_result(msg["id"], updated_item)

    @websocket_api.websocket_command({
        vol.Required("type"): WS_TYPE_REORDER_ITEMS,
        vol.Required("item_ids"): [str],
    })
    @websocket_api.async_response
    async def ws_reorder_items(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        item_ids = msg["item_ids"]
        success = await storage.async_reorder_items(item_ids)
        connection.send_result(msg["id"], {"success": success})

    @websocket_api.websocket_command({
        vol.Required("type"): WS_TYPE_SEND_SUMMARY,
        vol.Optional("force", default=True): bool,
    })
    @websocket_api.async_response
    async def ws_send_summary(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        force = msg.get("force", True)
        if notify_mgr:
            res = await notify_mgr.async_send_summary_report(force=force)
            if not res.get("success"):
                connection.send_error(msg["id"], "notify_failed", res.get("error", "发送通知失败"))
                return
            connection.send_result(msg["id"], res)
        else:
            # 降级尝试服务调用
            try:
                await hass.services.async_call(
                    DOMAIN,
                    "send_summary",
                    {"force": force},
                    blocking=True,
                )
                connection.send_result(msg["id"], {"success": True})
            except Exception as e:
                connection.send_error(msg["id"], "service_call_failed", str(e))

    @websocket_api.websocket_command({
        vol.Required("type"): WS_TYPE_GET_CONFIG,
    })
    @websocket_api.async_response
    async def ws_get_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        cfg = hass.data.get(DOMAIN, {}).get("config", {})
        connection.send_result(
            msg["id"],
            {
                "version": "1.1.1",
                "notify_service": cfg.get("notify_service"),
                "due_notification": cfg.get("due_notification"),
                "periodic_summary": cfg.get("periodic_summary"),
            },
        )

    # 依次安全注册各 WebSocket 命令 (忽略重复注册异常)
    for cmd in (
        ws_list_items,
        ws_save_item,
        ws_delete_item,
        ws_reset_item,
        ws_reorder_items,
        ws_send_summary,
        ws_get_config,
    ):
        try:
            websocket_api.async_register_command(hass, cmd)
        except Exception as e:
            _LOGGER.debug("Register ws command %s: %s", getattr(cmd, "_ws_type", "unknown"), e)
