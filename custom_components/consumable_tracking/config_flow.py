from typing import Any
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN

class ConsumableTrackingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """处理 consumable_tracking 集成的配置流程。"""
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """用户发起添加步骤。"""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="耗材与事务跟踪", data={})

        return self.async_show_form(step_id="user")
