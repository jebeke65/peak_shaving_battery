# CHANGES:
# - Registered the Options Flow correctly on the ConfigFlow class so the UI shows the "Options" (gear) button.
# - Kept existing OptionsFlowHandler and steps unchanged.
# - Minimal change: only moved async_get_options_flow to the correct place/signature.

from __future__ import annotations

from typing import Any, Dict

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    # inverter
    CONF_INVERTER_MODE_SELECT,
    CONF_OVERRULE_SELECT,
    # power sensors
    CONF_SOLAR_PRODUCTION,
    CONF_EV_CHARGE,
    CONF_CONSUMPTION,
    CONF_BATTERY_SOC,
    CONF_NET_POWER,
    CONF_PEAK_DEMAND,
    # controls
    CONF_BATTERY_REF,
    CONF_BATTERY_SLICER,
    CONF_ECO_MODE_POWER,
    CONF_DOD_ON_GRID,
    # NEW max power
    CONF_MAX_CHARGE_POWER_W,
    CONF_MAX_DISCHARGE_POWER_W,
    DEFAULT_MAX_CHARGE_POWER_W,
    DEFAULT_MAX_DISCHARGE_POWER_W,
    # notifications
    CONF_NOTIFY_SCRIPT,
    CONF_NOTIFY_DEVICE,
    # advanced
    CONF_VERBOSE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_VERBOSE,
)

DEFAULTS: Dict[str, Any] = {
    CONF_INVERTER_MODE_SELECT: "select.goodwe_inverter_operation_mode",
    CONF_OVERRULE_SELECT: "input_select.overrule_inverter_mode",
    CONF_SOLAR_PRODUCTION: "sensor.solar_production",
    CONF_EV_CHARGE: "sensor.verbeke_jan_load_verbeke_jan_ev",
    CONF_CONSUMPTION: "sensor.all_power_entities",
    CONF_BATTERY_SOC: "sensor.battery_state_of_charge",
    CONF_NET_POWER: "sensor.p1_meter_3c39e723fa3c_active_power",
    CONF_PEAK_DEMAND: "sensor.p1_meter_3c39e723fa3c_peak_demand_current_month",
    CONF_BATTERY_REF: "sensor.battery_reference_soc",
    CONF_BATTERY_SLICER: "input_number.battery_slicer",
    CONF_ECO_MODE_POWER: "number.goodwe_eco_mode_power",
    CONF_DOD_ON_GRID: "number.goodwe_depth_of_discharge_on_grid",
    # NEW defaults (old constants)
    CONF_MAX_CHARGE_POWER_W: DEFAULT_MAX_CHARGE_POWER_W,
    CONF_MAX_DISCHARGE_POWER_W: DEFAULT_MAX_DISCHARGE_POWER_W,
    CONF_NOTIFY_SCRIPT: "script.notify_user",
    CONF_NOTIFY_DEVICE: "Notify Jan",
    CONF_VERBOSE: DEFAULT_VERBOSE,
    CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
}


def _def(current: Dict[str, Any], key: str) -> Any:
    if key in current:
        return current[key]
    return DEFAULTS.get(key)


class PeakShavingBatteryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return PeakShavingBatteryOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_inverter()

    async def async_step_inverter(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_power_sensors()

        schema = vol.Schema(
            {
                vol.Required(CONF_INVERTER_MODE_SELECT, default=_def(self._data, CONF_INVERTER_MODE_SELECT)): str,
                vol.Required(CONF_OVERRULE_SELECT, default=_def(self._data, CONF_OVERRULE_SELECT)): str,
            }
        )
        return self.async_show_form(step_id="inverter", data_schema=schema)

    async def async_step_power_sensors(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_battery_controls()

        schema = vol.Schema(
            {
                vol.Required(CONF_SOLAR_PRODUCTION, default=_def(self._data, CONF_SOLAR_PRODUCTION)): str,
                vol.Required(CONF_CONSUMPTION, default=_def(self._data, CONF_CONSUMPTION)): str,
                vol.Required(CONF_EV_CHARGE, default=_def(self._data, CONF_EV_CHARGE)): str,
                vol.Required(CONF_NET_POWER, default=_def(self._data, CONF_NET_POWER)): str,
                vol.Required(CONF_PEAK_DEMAND, default=_def(self._data, CONF_PEAK_DEMAND)): str,
                vol.Required(CONF_BATTERY_SOC, default=_def(self._data, CONF_BATTERY_SOC)): str,
            }
        )
        return self.async_show_form(step_id="power_sensors", data_schema=schema)

    async def async_step_battery_controls(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_notifications()

        schema = vol.Schema(
            {
                vol.Required(CONF_BATTERY_REF, default=_def(self._data, CONF_BATTERY_REF)): str,
                vol.Required(CONF_BATTERY_SLICER, default=_def(self._data, CONF_BATTERY_SLICER)): str,
                vol.Required(CONF_ECO_MODE_POWER, default=_def(self._data, CONF_ECO_MODE_POWER)): str,
                vol.Optional(CONF_DOD_ON_GRID, default=_def(self._data, CONF_DOD_ON_GRID)): str,
                # NEW: max power (W)
                vol.Optional(CONF_MAX_CHARGE_POWER_W, default=_def(self._data, CONF_MAX_CHARGE_POWER_W)): int,
                vol.Optional(CONF_MAX_DISCHARGE_POWER_W, default=_def(self._data, CONF_MAX_DISCHARGE_POWER_W)): int,
            }
        )
        return self.async_show_form(step_id="battery_controls", data_schema=schema)

    async def async_step_notifications(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_advanced()

        schema = vol.Schema(
            {
                vol.Optional(CONF_NOTIFY_SCRIPT, default=_def(self._data, CONF_NOTIFY_SCRIPT)): str,
                vol.Optional(CONF_NOTIFY_DEVICE, default=_def(self._data, CONF_NOTIFY_DEVICE)): str,
            }
        )
        return self.async_show_form(step_id="notifications", data_schema=schema)

    async def async_step_advanced(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="Peak Shaving Battery Control", data=self._data)

        schema = vol.Schema(
            {
                vol.Optional(CONF_VERBOSE, default=_def(self._data, CONF_VERBOSE)): bool,
                vol.Optional(CONF_UPDATE_INTERVAL, default=_def(self._data, CONF_UPDATE_INTERVAL)): int,
            }
        )
        return self.async_show_form(step_id="advanced", data_schema=schema)


class PeakShavingBatteryOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._data = dict(config_entry.data) | dict(config_entry.options)

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_inverter(user_input)

    async def async_step_inverter(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_power_sensors()

        schema = vol.Schema(
            {
                vol.Required(CONF_INVERTER_MODE_SELECT, default=_def(self._data, CONF_INVERTER_MODE_SELECT)): str,
                vol.Required(CONF_OVERRULE_SELECT, default=_def(self._data, CONF_OVERRULE_SELECT)): str,
            }
        )
        return self.async_show_form(step_id="inverter", data_schema=schema)

    async def async_step_power_sensors(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_battery_controls()

        schema = vol.Schema(
            {
                vol.Required(CONF_SOLAR_PRODUCTION, default=_def(self._data, CONF_SOLAR_PRODUCTION)): str,
                vol.Required(CONF_CONSUMPTION, default=_def(self._data, CONF_CONSUMPTION)): str,
                vol.Required(CONF_EV_CHARGE, default=_def(self._data, CONF_EV_CHARGE)): str,
                vol.Required(CONF_NET_POWER, default=_def(self._data, CONF_NET_POWER)): str,
                vol.Required(CONF_PEAK_DEMAND, default=_def(self._data, CONF_PEAK_DEMAND)): str,
                vol.Required(CONF_BATTERY_SOC, default=_def(self._data, CONF_BATTERY_SOC)): str,
            }
        )
        return self.async_show_form(step_id="power_sensors", data_schema=schema)

    async def async_step_battery_controls(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_notifications()

        schema = vol.Schema(
            {
                vol.Required(CONF_BATTERY_REF, default=_def(self._data, CONF_BATTERY_REF)): str,
                vol.Required(CONF_BATTERY_SLICER, default=_def(self._data, CONF_BATTERY_SLICER)): str,
                vol.Required(CONF_ECO_MODE_POWER, default=_def(self._data, CONF_ECO_MODE_POWER)): str,
                vol.Optional(CONF_DOD_ON_GRID, default=_def(self._data, CONF_DOD_ON_GRID)): str,
                # NEW: max power (W)
                vol.Optional(CONF_MAX_CHARGE_POWER_W, default=_def(self._data, CONF_MAX_CHARGE_POWER_W)): int,
                vol.Optional(CONF_MAX_DISCHARGE_POWER_W, default=_def(self._data, CONF_MAX_DISCHARGE_POWER_W)): int,
            }
        )
        return self.async_show_form(step_id="battery_controls", data_schema=schema)

    async def async_step_notifications(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_advanced()

        schema = vol.Schema(
            {
                vol.Optional(CONF_NOTIFY_SCRIPT, default=_def(self._data, CONF_NOTIFY_SCRIPT)): str,
                vol.Optional(CONF_NOTIFY_DEVICE, default=_def(self._data, CONF_NOTIFY_DEVICE)): str,
            }
        )
        return self.async_show_form(step_id="notifications", data_schema=schema)

    async def async_step_advanced(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(CONF_VERBOSE, default=_def(self._data, CONF_VERBOSE)): bool,
                vol.Optional(CONF_UPDATE_INTERVAL, default=_def(self._data, CONF_UPDATE_INTERVAL)): int,
            }
        )
        return self.async_show_form(step_id="advanced", data_schema=schema)
