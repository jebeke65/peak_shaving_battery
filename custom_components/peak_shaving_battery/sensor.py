from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PeakShavingBatteryCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PeakShavingBatteryCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        [
            BatteryManualStatusSensor(coordinator, entry),
            BatterySocTargetSensor(coordinator, entry),
        ]
    )


class BatteryManualStatusSensor(CoordinatorEntity[PeakShavingBatteryCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: PeakShavingBatteryCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_battery_manual_status"
        self._attr_name = "Battery Manual Status"

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        return data.get("status_state")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data or {}
        return data.get("status_attributes", {})


class BatterySocTargetSensor(CoordinatorEntity[PeakShavingBatteryCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: PeakShavingBatteryCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_battery_soc_target"
        self._attr_name = "Battery SOC Target %"

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        return data.get("lowest_min_state")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data or {}
        return data.get("lowest_min_attributes", {})
