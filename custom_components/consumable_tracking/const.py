"""耗材与事务跟踪常量定义 / Constants for Consumable Tracking."""

DOMAIN = "consumable_tracking"
STORAGE_KEY = "consumable_tracking"
STORAGE_VERSION = 1

# 配置键名
CONF_NOTIFY_SERVICE = "notify_service"
CONF_CHECK_TIME = "check_time"
CONF_DUE_NOTIFICATION = "due_notification"
CONF_PERIODIC_SUMMARY = "periodic_summary"
CONF_ENABLED = "enabled"
CONF_REMIND_DAYS = "remind_days"
CONF_INTERVAL_MONTHS = "interval_months"
CONF_NOTIFY_DAY = "notify_day"
CONF_NOTIFY_TIME = "notify_time"

# 默认配置值
DEFAULT_NOTIFY_SERVICE = "notify.wework"
DEFAULT_CHECK_TIME = "09:30:00"
DEFAULT_REMIND_DAYS = [14, 7, 0]
DEFAULT_DUE_REMIND_DAYS = DEFAULT_REMIND_DAYS
DEFAULT_INTERVAL_MONTHS = 3
DEFAULT_PERIODIC_MONTHS = DEFAULT_INTERVAL_MONTHS
DEFAULT_NOTIFY_DAY = 1
DEFAULT_PERIODIC_NOTIFY_DAY = DEFAULT_NOTIFY_DAY
DEFAULT_NOTIFY_TIME = "10:00:00"
DEFAULT_PERIODIC_NOTIFY_TIME = DEFAULT_NOTIFY_TIME

# 耗材属性常量
ATTR_ITEMS = "items"
ATTR_ITEM_ID = "item_id"
ATTR_NAME = "name"
ATTR_CATEGORY = "category"
ATTR_ICON = "icon"
ATTR_START_DATE = "start_date"
ATTR_DURATION_VALUE = "duration_value"
ATTR_DURATION_UNIT = "duration_unit"
ATTR_EXPECTED_END_DATE = "expected_end_date"
ATTR_NOTE = "note"
ATTR_HISTORY = "history"
ATTR_LAST_NOTIFIED = "last_notified"
ATTR_DAYS_REMAINING = "days_remaining"
ATTR_PROGRESS = "progress"
ATTR_STATUS = "status"

# 服务定义
SERVICE_ADD_ITEM = "add_item"
SERVICE_UPDATE_ITEM = "update_item"
SERVICE_DELETE_ITEM = "delete_item"
SERVICE_RESET_ITEM = "reset_item"
SERVICE_TRIGGER_CHECK = "trigger_check"
SERVICE_SEND_SUMMARY = "send_summary"
SERVICE_REORDER_ITEMS = "reorder_items"

# WebSocket 接口定义
WS_TYPE_LIST_ITEMS = f"{DOMAIN}/list_items"
WS_TYPE_SAVE_ITEM = f"{DOMAIN}/save_item"
WS_TYPE_DELETE_ITEM = f"{DOMAIN}/delete_item"
WS_TYPE_RESET_ITEM = f"{DOMAIN}/reset_item"
WS_TYPE_REORDER_ITEMS = f"{DOMAIN}/reorder_items"
WS_TYPE_SEND_SUMMARY = f"{DOMAIN}/send_summary"
WS_TYPE_GET_CONFIG = f"{DOMAIN}/get_config"

# 卡片前端静态资源路径
FRONTEND_URL_PATH = f"/{DOMAIN}"
CARD_FILENAME = "consumable-tracking-card.js"
CARD_URL = f"{FRONTEND_URL_PATH}/{CARD_FILENAME}"
