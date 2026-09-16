"""耗材与事务跟踪主集成 / Main entry for Consumable Tracking integration."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.event import async_track_time_change

from .const import (
    CARD_FILENAME,
    CARD_URL,
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
    DOMAIN,
    FRONTEND_URL_PATH,
    SERVICE_ADD_ITEM,
    SERVICE_DELETE_ITEM,
    SERVICE_RESET_ITEM,
    SERVICE_SEND_SUMMARY,
    SERVICE_TRIGGER_CHECK,
    SERVICE_UPDATE_ITEM,
)
from .notify import NotificationManager
from .storage import ConsumableStorage
from .websocket import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)

# 配置校验 Schema
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_NOTIFY_SERVICE, default=DEFAULT_NOTIFY_SERVICE): cv.string,
                vol.Optional(CONF_CHECK_TIME, default=DEFAULT_CHECK_TIME): cv.string,
                vol.Optional(CONF_DUE_NOTIFICATION, default={}): vol.Schema(
                    {
                        vol.Optional(CONF_ENABLED, default=True): cv.boolean,
                        vol.Optional(CONF_REMIND_DAYS, default=DEFAULT_REMIND_DAYS): vol.All(
                            cv.ensure_list, [cv.positive_int]
                        ),
                    }
                ),
                vol.Optional(CONF_PERIODIC_SUMMARY, default={}): vol.Schema(
                    {
                        vol.Optional(CONF_ENABLED, default=True): cv.boolean,
                        vol.Optional(CONF_INTERVAL_MONTHS, default=DEFAULT_INTERVAL_MONTHS): cv.positive_int,
                        vol.Optional(CONF_NOTIFY_DAY, default=DEFAULT_NOTIFY_DAY): cv.positive_int,
                        vol.Optional(CONF_NOTIFY_TIME, default=DEFAULT_NOTIFY_TIME): cv.string,
                    }
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """初始化 consumable_tracking 集成."""
    conf = config.get(DOMAIN, {})

    # 1. 初始化持久化存储
    storage = ConsumableStorage(hass)
    await storage.async_load()

    # 2. 初始化通知管理器
    notify_mgr = NotificationManager(hass, storage, conf)

    hass.data[DOMAIN] = {
        "storage": storage,
        "notify_mgr": notify_mgr,
        "config": conf,
    }

    # 3. 注册静态资源路径 (前端卡片)
    card_path = os.path.join(os.path.dirname(__file__), CARD_FILENAME)
    if hasattr(hass.http, "async_register_static_paths"):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, card_path, cache_headers=False)]
        )
    else:
        hass.http.register_static_path(CARD_URL, card_path, cache_headers=False)

    # 4. 自动注入前端 extra_js_url 与 Lovelace 资源 (免用户手动添加 Resources)
    try:
        from homeassistant.components.frontend import add_extra_js_url
        add_extra_js_url(hass, f"{CARD_URL}?v=1.0.1")
        _LOGGER.debug("已通过 add_extra_js_url 自动注入前端卡片")
    except Exception as ex:
        _LOGGER.debug("add_extra_js_url 注入失败或不可用: %s", ex)

    # 同时尝试自动注册至 Lovelace storage resources (兼容 Cast 及原生加载)
    async def _async_register_lovelace_resource(_event=None) -> None:
        try:
            lovelace = hass.data.get("lovelace")
            if lovelace and hasattr(lovelace, "resources"):
                resources = lovelace.resources
                if not getattr(resources, "loaded", True) and hasattr(resources, "async_load"):
                    await resources.async_load()
                
                # 检查是否已存在
                existing = [
                    r for r in resources.async_items()
                    if r.get("url", "").split("?")[0] == CARD_URL
                ]
                if not existing:
                    _LOGGER.info("正在自动向 Lovelace 添加 consumable-tracking-card 资源")
                    await resources.async_create_item({
                        "res_type": "module",
                        "url": f"{CARD_URL}?v=1.0.1",
                    })
                else:
                    _LOGGER.debug("Lovelace 资源中已存在 consumable-tracking-card")
        except Exception as err:
            _LOGGER.debug("自动向 Lovelace 注册资源跳过: %s", err)

    if hass.state == CoreState.running:
        await _async_register_lovelace_resource()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_register_lovelace_resource)

    # 4. 注册 WebSocket API
    async_register_websocket_api(hass, storage)

    # 5. 加载传感器平台
    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

    # 6. 注册定时任务 (每日巡检)
    check_time_str = conf.get(CONF_CHECK_TIME, DEFAULT_CHECK_TIME)
    try:
        parts = [int(p) for p in str(check_time_str).split(":")]
        c_hour, c_min, c_sec = (parts[0], parts[1], parts[2] if len(parts) > 2 else 0)
    except Exception:
        c_hour, c_min, c_sec = (9, 30, 0)

    async def _handle_daily_check(now: datetime) -> None:
        """每日定时巡检即将到期耗材."""
        _LOGGER.debug("触发每日耗材到期状态巡检")
        await notify_mgr.async_check_due_items()

        # 检查是否为汇总报告推送日
        summary_cfg = conf.get(CONF_PERIODIC_SUMMARY, {})
        target_day = summary_cfg.get(CONF_NOTIFY_DAY, DEFAULT_NOTIFY_DAY)
        if now.day == target_day:
            await notify_mgr.async_send_summary_report(force=False)

    async_track_time_change(
        hass,
        _handle_daily_check,
        hour=c_hour,
        minute=c_min,
        second=c_sec,
    )

    # 7. 注册 HA Services (供用户自动化或开发者工具手动调用)
    async def handle_add_item(call: ServiceCall) -> None:
        await storage.async_save_item(call.data)
        hass.bus.async_fire(f"{DOMAIN}_updated", {"action": "save", "item": call.data})

    async def handle_update_item(call: ServiceCall) -> None:
        await storage.async_save_item(call.data)
        hass.bus.async_fire(f"{DOMAIN}_updated", {"action": "save", "item": call.data})

    async def handle_delete_item(call: ServiceCall) -> None:
        item_id = call.data.get("item_id")
        if item_id:
            await storage.async_delete_item(item_id)
            hass.bus.async_fire(f"{DOMAIN}_updated", {"action": "delete", "item_id": item_id})

    async def handle_reset_item(call: ServiceCall) -> None:
        item_id = call.data.get("item_id")
        new_start = call.data.get("new_start_date")
        note = call.data.get("note", "")
        if item_id:
            res = await storage.async_reset_item(item_id, new_start, note)
            hass.bus.async_fire(f"{DOMAIN}_updated", {"action": "reset", "item": res})

    async def handle_trigger_check(call: ServiceCall) -> None:
        await notify_mgr.async_check_due_items()

    async def handle_send_summary(call: ServiceCall) -> None:
        force = call.data.get("force", True)
        await notify_mgr.async_send_summary_report(force=force)

    hass.services.async_register(DOMAIN, SERVICE_ADD_ITEM, handle_add_item)
    hass.services.async_register(DOMAIN, SERVICE_UPDATE_ITEM, handle_update_item)
    hass.services.async_register(DOMAIN, SERVICE_DELETE_ITEM, handle_delete_item)
    hass.services.async_register(DOMAIN, SERVICE_RESET_ITEM, handle_reset_item)
    hass.services.async_register(DOMAIN, SERVICE_TRIGGER_CHECK, handle_trigger_check)
    hass.services.async_register(DOMAIN, SERVICE_SEND_SUMMARY, handle_send_summary)

    _LOGGER.info("consumable_tracking (耗材与事务跟踪) 插件初始化成功")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """通过 UI 添加集成条目时的初始化。"""
    if DOMAIN not in hass.data:
        await async_setup(hass, {})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载 UI 集成条目。"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok
