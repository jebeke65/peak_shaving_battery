# CHANGES:
# - Replaced hardcoded 5000/4300 with UI-configurable max_charge_power_w / max_discharge_power_w.
# - Added safe fallback to defaults if values are missing/invalid (and prevent divide-by-zero).
# - No renames/refactor; minimal inline change at amount_charge/amount_discharge calculation.
# - Kept behavior identical when defaults are used.

from __future__ import annotations

import logging
from typing import Any, Dict

from datetime import timedelta

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE

from .const import (
    # inverter
    CONF_INVERTER_MODE_SELECT,
    CONF_OVERRULE_SELECT,
    # sensors
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
    DEFAULT_VERBOSE,
)

_LOGGER = logging.getLogger(__name__)


class PeakShavingBatteryCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Coordinator: berekent modus + stuurt inverter/controls, levert sensordata."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: Dict[str, Any],
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Peak Shaving Battery Control",
            update_interval=update_interval,
        )
        self._config = config
        self._previous_values: Dict[str, float] = {}
        self._verbose = bool(config.get(CONF_VERBOSE, DEFAULT_VERBOSE))

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update config at runtime (used by options listener)."""
        self._config = new_config
        self._verbose = bool(new_config.get(CONF_VERBOSE, DEFAULT_VERBOSE))

    # ---------------- helpers ----------------
    def _vlog(self, msg: str) -> None:
        """Log only when UI toggle is enabled."""
        if self._verbose:
            _LOGGER.info(msg)

    def _get_state(self, entity_id: str) -> State | None:
        return self.hass.states.get(entity_id)

    def _get_float_state(self, entity_id: str, fallback: float = 0.0) -> float:
        st = self._get_state(entity_id)
        if st is None or st.state in (STATE_UNKNOWN, STATE_UNAVAILABLE, None):
            self._vlog(f"Invalid/unknown for {entity_id}, fallback: {fallback}")
            return self._previous_values.get(entity_id, fallback)

        try:
            val = float(st.state)
            self._previous_values[entity_id] = val
            return val
        except (ValueError, TypeError):
            self._vlog(f"Could not parse float for {entity_id}='{st.state}', fallback={fallback}")
            return self._previous_values.get(entity_id, fallback)

    async def _set_inverter_mode_if_needed(self, desired_mode: str) -> None:
        entity_id = self._config[CONF_INVERTER_MODE_SELECT]
        st = self._get_state(entity_id)
        current_mode = st.state if st else None

        if current_mode != desired_mode:
            self._vlog(f". (o) Changing inverter mode from {current_mode} to {desired_mode}")
            await self.hass.services.async_call(
                "select",
                "select_option",
                {"entity_id": entity_id, "option": desired_mode},
                blocking=False,
            )
        else:
            self._vlog(f". (o) Inverter already in mode '{desired_mode}', no action needed.")

    async def _call_number_or_input_number(self, entity_id: str, value: float) -> None:
        domain = entity_id.split(".")[0]
        if domain == "number":
            await self.hass.services.async_call(
                "number", "set_value", {"entity_id": entity_id, "value": value}, blocking=False
            )
        elif domain == "input_number":
            await self.hass.services.async_call(
                "input_number", "set_value", {"entity_id": entity_id, "value": value}, blocking=False
            )
        else:
            _LOGGER.warning("Unsupported entity for set_value: %s", entity_id)

    async def _set_value_if_needed(
        self,
        entity_id: str,
        desired_value: float,
        tolerance: float = 0.5,
    ) -> None:
        st = self._get_state(entity_id)
        if st is None or st.state in (STATE_UNKNOWN, STATE_UNAVAILABLE, None):
            self._vlog(f". (o) {entity_id} invalid/unknown, setting to {desired_value}")
            await self._call_number_or_input_number(entity_id, desired_value)
            return

        try:
            current_value = float(st.state)
        except (ValueError, TypeError):
            self._vlog(f". (o) Could not parse current value of {entity_id}, setting anyway.")
            await self._call_number_or_input_number(entity_id, desired_value)
            return

        if abs(current_value - desired_value) > tolerance:
            self._vlog(f". (o) Setting {entity_id} from {current_value} to {desired_value}")
            await self._call_number_or_input_number(entity_id, desired_value)
        else:
            self._vlog(f". (o) {entity_id} already at {current_value}, no change needed.")

    async def _notify_user(self, message: str, critical: bool = False) -> None:
        script_entity = self._config.get(CONF_NOTIFY_SCRIPT)
        device = self._config.get(CONF_NOTIFY_DEVICE)

        if not script_entity:
            _LOGGER.warning("Notification requested, but no notify_script configured")
            return

        variables: Dict[str, Any] = {"message": message, "critical": 1 if critical else 0}
        if device:
            variables["device"] = device

        await self.hass.services.async_call(
            "script",
            "turn_on",
            {"entity_id": script_entity, "variables": variables},
            blocking=False,
        )

    # ---------------- main update ----------------
    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            self._vlog("==================== PEAK SHAVING BATTERY RUN ====================")
            self._vlog("Inputs")

            inverter_mode_entity = self._config[CONF_INVERTER_MODE_SELECT]
            overrule_entity = self._config[CONF_OVERRULE_SELECT]

            inverter_mode_state = self._get_state(inverter_mode_entity)
            inverter_mode = inverter_mode_state.state if inverter_mode_state else "unknown"
            overrule_state = self._get_state(overrule_entity)
            overrule_value = str(overrule_state.state if overrule_state else "").strip()

            self._vlog(f". (i) Current inverter mode: {inverter_mode}")
            self._vlog(f". (i) Overrule setting: {overrule_value}")

            production_raw = self._get_float_state(self._config[CONF_SOLAR_PRODUCTION])
            car_charge = self._get_float_state(self._config[CONF_EV_CHARGE])
            consumption = self._get_float_state(self._config[CONF_CONSUMPTION])
            battery_percentage = self._get_float_state(self._config[CONF_BATTERY_SOC])
            current_from_net = self._get_float_state(self._config[CONF_NET_POWER])

            self._vlog(f". (i) Production: {production_raw}")
            self._vlog(f". (i) Car Charge: {car_charge}")
            self._vlog(f". (i) Consumption: {consumption}")
            self._vlog(f". (i) Battery %: {battery_percentage}")
            self._vlog(f". (i) Net: {current_from_net}")
            self._vlog("Outputs")

            nsurplus = production_raw - consumption + car_charge
            surplus = production_raw > consumption > 0

            # battery SOC target %
            battery_lowest = self._get_float_state(self._config[CONF_BATTERY_REF])
            abovemin = battery_percentage > battery_lowest
            current_mode_flag = surplus or abovemin

            self._vlog(f". (o) Battery SOC Target %: {battery_lowest}")
            self._vlog(f". (o) Surplus: {surplus}, Above Target: {abovemin} => Manual Mode: {not current_mode_flag}")

            total_netto = consumption - production_raw
            if total_netto < 0:
                self._vlog(". (o) total_netto < 0, adjusting to 1200")
                total_netto = 1200

            peak = max(self._get_float_state(self._config[CONF_PEAK_DEMAND]), 2600)
            slicer = min(self._get_float_state(self._config[CONF_BATTERY_SLICER]), 10)

            from_net = peak * (100 - slicer) / 100
            from_battery = total_netto - from_net

            # NEW: max power from UI (safe fallback)
            try:
                max_charge_w = float(self._config.get(CONF_MAX_CHARGE_POWER_W, DEFAULT_MAX_CHARGE_POWER_W))
            except (TypeError, ValueError):
                max_charge_w = float(DEFAULT_MAX_CHARGE_POWER_W)

            try:
                max_discharge_w = float(self._config.get(CONF_MAX_DISCHARGE_POWER_W, DEFAULT_MAX_DISCHARGE_POWER_W))
            except (TypeError, ValueError):
                max_discharge_w = float(DEFAULT_MAX_DISCHARGE_POWER_W)

            if max_charge_w <= 0:
                max_charge_w = float(DEFAULT_MAX_CHARGE_POWER_W)
            if max_discharge_w <= 0:
                max_discharge_w = float(DEFAULT_MAX_DISCHARGE_POWER_W)

            amount_charge = abs(int(from_battery / max_charge_w * 100))
            amount_discharge = abs(int(from_battery / max_discharge_w * 100)) + 3

            charge = from_battery < 0
            if current_from_net > peak:
                self._vlog(". (o) Net draw exceeds peak; disabling charge")
                charge = False

            calculated_state = "general" if current_mode_flag else ("Charge" if charge else "Discharge")

            self._vlog(f". (o) Calculated mode: {calculated_state}")
            self._vlog(f". (o) from_net: {from_net}")
            self._vlog(f". (o) from_battery: {from_battery}")
            self._vlog(f". (o) amount_charge: {amount_charge}")
            self._vlog(f". (o) amount_discharge: {amount_discharge}")

            # Final mode (eco_discharge disabled)
            eco_amount_calc = amount_charge if charge else amount_discharge

            if overrule_value == "Automatic":
                if calculated_state == "Charge":
                    desired_mode = "eco_charge"
                    eco_to_write = eco_amount_calc
                else:
                    desired_mode = "general"
                    eco_to_write = None
            elif overrule_value == "General":
                desired_mode = "general"
                eco_to_write = None
            elif overrule_value == "Charge":
                desired_mode = "eco_charge"
                eco_to_write = max(1, int(eco_amount_calc))
            elif overrule_value == "Discharge":
                self._vlog(". (o) Overrule 'Discharge' requested, using 'general' (eco_discharge disabled)")
                desired_mode = "general"
                eco_to_write = None
            else:
                self._vlog(f". (o) Overrule: Unknown option '{overrule_value}', fallback to 'general'")
                desired_mode = "general"
                eco_to_write = None

            await self._set_inverter_mode_if_needed(desired_mode)

            if desired_mode == "eco_charge" and eco_to_write is not None:
                eco_pct = max(0, min(100, int(eco_to_write)))
                await self._set_value_if_needed(self._config[CONF_ECO_MODE_POWER], eco_pct)

            if desired_mode != "general":
                await self._set_value_if_needed(self._config[CONF_BATTERY_SLICER], battery_percentage)

            dod_entity = self._config.get(CONF_DOD_ON_GRID)
            if dod_entity:
                await self._set_value_if_needed(dod_entity, 90)

            status_attributes = {
                "oBattery SOC Target %": battery_lowest,
                "oSurplus": surplus,
                "oAbove Target": abovemin,
                "oFrom net": from_net,
                "oFrom battery": from_battery,
                "oAmount charge": amount_charge,
                "oAmount discharge": amount_discharge,
                "oCalculated mode": calculated_state,
                "oFinal mode": desired_mode,
                "oTotal netto": total_netto,
                "oSurplus power": nsurplus,
                "oBattery percentage": battery_percentage,
                "oBattery/Car Balance": slicer,
                "oInverter Charge/Discharge %": 0 if eco_to_write is None else int(eco_to_write),
                "oCharge mode": charge,
                "iInverter overrule operating mode": overrule_value,
                "iMax charge power (W)": int(max_charge_w),
                "iMax discharge power (W)": int(max_discharge_w),
            }

            lowest_min_attributes = {
                "unit_of_measurement": "%",
                "state_class": "measurement",
            }

            return {
                "status_state": calculated_state,
                "status_attributes": status_attributes,
                "lowest_min_state": battery_lowest,
                "lowest_min_attributes": lowest_min_attributes,
            }

        except Exception as err:
            _LOGGER.exception("Error in Peak Shaving Battery Control: %s", err)
            await self._notify_user(f"Battery App Error: {err}", critical=True)
            raise UpdateFailed(str(err)) from err
