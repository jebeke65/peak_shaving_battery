# CHANGES:
# - Added UI-configurable constants for max charge/discharge power (W).
# - Kept existing defaults (5000W charge, 4300W discharge) to preserve behavior.
# - No renames/refactor; only minimal new constants and defaults.

from __future__ import annotations

DOMAIN = "peak_shaving_battery"

# Inverter
CONF_INVERTER_MODE_SELECT = "inverter_mode_select"
CONF_OVERRULE_SELECT = "overrule_select"

# Power sensors
CONF_SOLAR_PRODUCTION = "solar_production_sensor"
CONF_EV_CHARGE = "ev_charge_sensor"
CONF_CONSUMPTION = "consumption_sensor"
CONF_BATTERY_SOC = "battery_soc_sensor"
CONF_NET_POWER = "net_power_sensor"
CONF_PEAK_DEMAND = "peak_demand_sensor"

# Controls
CONF_BATTERY_REF = "battery_reference_sensor"
CONF_BATTERY_SLICER = "battery_slicer_number"
CONF_ECO_MODE_POWER = "eco_mode_power_number"
CONF_DOD_ON_GRID = "dod_on_grid_number"

# NEW: max inverter/battery power limits (W)
CONF_MAX_CHARGE_POWER_W = "max_charge_power_w"
CONF_MAX_DISCHARGE_POWER_W = "max_discharge_power_w"

# Notifications
CONF_NOTIFY_SCRIPT = "notify_script"
CONF_NOTIFY_DEVICE = "notify_device"

# Advanced
CONF_VERBOSE = "verbose_logging"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL = 5  # seconds
DEFAULT_VERBOSE = True

# NEW defaults (match your existing hardcoded constants)
DEFAULT_MAX_CHARGE_POWER_W = 5000
DEFAULT_MAX_DISCHARGE_POWER_W = 4300
