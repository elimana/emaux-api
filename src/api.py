"""API for interacting with an Emaux SPV pool pump.

This module provides an API client for communicating with Emaux SPV pool pumps over HTTP.
It enables getting pump data, setting speeds, and controlling power state.
"""

import logging
import math
from typing import Any

import aiohttp
from datetime import datetime, timezone
from aiohttp import ClientTimeout

_LOGGER = logging.getLogger(__name__)

from dataclasses import dataclass
from typing import Optional

@dataclass
class EmauxPumpData:
    """Data class for Emaux pump data."""
    current_time: str
    current_speed: int
    current_watts: int
    running_status: bool
    fault_flag: int
    fault_code: str
    speed_selected: int
    current_temperature: int
    free_mode_status: bool
    current_schedule: int
    current_gpm: int
    speed_count: int
    schedule_count: int
    model: str

    @classmethod
    def from_dict(cls, data: dict) -> "EmauxPumpData":
        """Create instance from dictionary."""
        return cls(
            current_time=data["CurrentTime"],
            current_speed=int(data["CurrentSpeed"]),
            current_watts=int(data["CurrentWatts"]),
            running_status=data["RunningStatus"] == "1",
            fault_flag=int(data["FaultFlag"]),
            fault_code=data["FaultCode"],
            speed_selected=int(data["SpeedSelected"]),
            current_temperature=int(data["CurrentTemperuture"]),  # Note: API has typo in 'Temperature'
            free_mode_status=data["FreeModeStatus"] == "1",
            current_schedule=int(data["CurrentSchedule"]),
            current_gpm=int(data["CurrentGPM"]),
            speed_count=int(data["SpeedCount"]),
            schedule_count=int(data["ScheduleCount"]),
            model=data["Model"]
        )

@dataclass
class Schedule:
    """Data class for schedule settings."""
    enabled: bool
    time_on_hour: int
    time_on_min: int
    time_off_hour: int
    time_off_min: int
    speed_select: int
    title: str

@dataclass
class EmauxPumpSettings:
    """Data class for Emaux pump settings."""
    current_min: int
    current_hour: int
    run_stop: bool
    set_current_speed: int
    set_speed_selected: int
    speeds: list[int]
    speed_titles: list[str]
    schedules: list[Schedule]
    language: int
    lang_sel: str
    frozen_enable: bool
    frozen_lasting_time: int
    frozen_speed: int
    frozen_temperature: int
    wifi_set_to_default: bool
    reset: bool

    @classmethod
    def from_dict(cls, data: dict) -> "EmauxPumpSettings":
        """Create instance from dictionary."""
        # Process speeds and titles
        speeds = [
            int(data["Speed1"]), int(data["Speed2"]),
            int(data["Speed3"]), int(data["Speed4"])
        ]
        speed_titles = [
            data["Speed1Title"], data["Speed2Title"],
            data["Speed3Title"], data["Speed4Title"]
        ]

        # Process schedules
        schedules = []
        for i in range(1, 5):
            schedule = Schedule(
                enabled=data[f"Sch{i}En"] == "1",
                time_on_hour=int(data[f"Sch{i}TimeOnHour"]),
                time_on_min=int(data[f"Sch{i}TimeOnMin"]),
                time_off_hour=int(data[f"Sch{i}TimeOffHour"]),
                time_off_min=int(data[f"Sch{i}TimeOffMin"]),
                speed_select=int(data[f"Sch{i}SpeedSelect"]),
                title=data[f"SchTitle{i}"]
            )
            schedules.append(schedule)

        return cls(
            current_min=int(data["CurrentMin"]),
            current_hour=int(data["CurrentHour"]),
            run_stop=data["RunStop"] == "1",
            set_current_speed=int(data["SetCurrentSpeed"]),
            set_speed_selected=int(data["SetSpeedSelected"]),
            speeds=speeds,
            speed_titles=speed_titles,
            schedules=schedules,
            language=int(data["Language"]),
            lang_sel=data["LangSel"],
            frozen_enable=data["Frozen_Enable"] == "1",
            frozen_lasting_time=int(data["Frozen_LastingTime"]),
            frozen_speed=int(data["Frozen_Speed"]),
            frozen_temperature=int(data["Frozen_Temperature"]),
            wifi_set_to_default=data["WifiSetToDefault"] == "1",
            reset=data["Reset"] == "1"
        )
@dataclass
class EmauxData:
    """Data class for Emaux data."""
    pump: EmauxPumpData
    settings: EmauxPumpSettings

# Valid parameters and their value ranges
VALID_PARAMETERS = {
    # Basic Operation
    "RunStop": (1, 2),  # Off/On
    "SetCurrentSpeed": (800, 3400),  # Min/Max speed
    "SetSpeedSelected": (1, 4),  # Speed presets 1-4
    
    # Speed Presets
    "Speed1": (800, 3400),
    "Speed2": (800, 3400),
    "Speed3": (800, 3400),
    "Speed4": (800, 3400),
    
    # Speed Titles
    "Speed1Title": None,  # String value
    "Speed2Title": None,  # String value
    "Speed3Title": None,  # String value
    "Speed4Title": None,  # String value
    
    # Schedule Enables
    "Sch1En": (0, 1),
    "Sch2En": (0, 1),
    "Sch3En": (0, 1),
    "Sch4En": (0, 1),
    
    # Schedule Times
    "Sch1TimeOnHour": (0, 23),
    "Sch2TimeOnHour": (0, 23),
    "Sch3TimeOnHour": (0, 23),
    "Sch4TimeOnHour": (0, 23),
    "Sch1TimeOnMin": (0, 59),
    "Sch2TimeOnMin": (0, 59),
    "Sch3TimeOnMin": (0, 59),
    "Sch4TimeOnMin": (0, 59),
    "Sch1TimeOffHour": (0, 23),
    "Sch2TimeOffHour": (0, 23),
    "Sch3TimeOffHour": (0, 23),
    "Sch4TimeOffHour": (0, 23),
    "Sch1TimeOffMin": (0, 59),
    "Sch2TimeOffMin": (0, 59),
    "Sch3TimeOffMin": (0, 59),
    "Sch4TimeOffMin": (0, 59),
    
    # Schedule Speed Selections
    "Sch1SpeedSelect": (1, 4),
    "Sch2SpeedSelect": (1, 4),
    "Sch3SpeedSelect": (1, 4),
    "Sch4SpeedSelect": (1, 4),
    
    # Schedule Titles
    "SchTitle1": None,  # String value
    "SchTitle2": None,  # String value
    "SchTitle3": None,  # String value
    "SchTitle4": None,  # String value
    
    # Freeze Protection
    "Frozen_Enable": (0, 1),
    "Frozen_LastingTime": (1, 12),  # Hours
    "Frozen_Speed": (1200, 3450),
    "Frozen_Temperature": (2, 10),  # Celsius
    
    # System Settings
    "Language": (0),  # Assuming 6 language options
    "LangSel": {"en", "cn", "fr", "de", "es", "it", "ru"},  # String value
    "WifiSetToDefault": (0, 1),
    "Reset": (0, 1)
}

class API:
    """Class for example API."""

    def __init__(self, host: str, timeout: int = 5) -> None:
        """Initialise."""
        self.host = host
        self.api_url = f"http://{host}/cgi-bin/EpvCgi"
        self.timeout = ClientTimeout(total=timeout)

    def utc_now(self) -> int:
        utc_now = math.floor(datetime.now(timezone.utc).timestamp() * 1000)
        return utc_now

    async def get_data(self) -> EmauxPumpData:
        """Get api data."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}?name=AllRd&val=0&type=get&time={self.utc_now()}", timeout=self.timeout) as response:
                    return EmauxPumpData.from_dict(await response.json())
        except aiohttp.ClientError as err:
            raise APIConnectionError("Timeout connecting to api") from err

    async def set_speed(self, speed: int) -> bool:
        """Set the pump speed."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}?name=SetCurrentSpeed&val={speed}&type=set&time={self.utc_now()}", timeout=self.timeout) as response:
                    _LOGGER.debug("Pump speed set to %s, status code: %s", speed, response.status)
                    return (response.status == 200) and (await response.json() == {"SetCurrentSpeed": speed})
        except aiohttp.ClientError as err:
            raise APIConnectionError("Timeout connecting to api") from err

    async def turn_on(self) -> bool:
        """Turn on the pump."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}?name=RunStop&val=1&type=set&time={self.utc_now()}", timeout=self.timeout) as response:
                    _LOGGER.debug("Pump turned on, status code: %s", response.status)
                    return (response.status == 200) and (await response.json() == {"RunStop": 1})
        except aiohttp.ClientError as err:
            raise APIConnectionError("Timeout connecting to api") from err

    async def turn_off(self) -> bool:
        """Turn off the pump."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}?name=RunStop&val=2&type=set&time={self.utc_now()}", timeout=self.timeout) as response:
                    _LOGGER.debug("Pump turned off, status code: %s", response.status)
                    return (response.status == 200) and (await response.json() == {"RunStop": 2})
        except aiohttp.ClientError as err:
            raise APIConnectionError("Timeout connecting to api") from err

    async def get_settings(self) -> EmauxPumpSettings:
        """Get the pump settings."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}?name=AllWr&val=0&type=get&time={self.utc_now()}", timeout=self.timeout) as response:
                    return EmauxPumpSettings.from_dict(await response.json())
        except aiohttp.ClientError as err:
            raise APIConnectionError("Timeout connecting to api") from err
    
    async def set_parameter(self, name: str, value: Any) -> bool:
        """Set a parameter."""
        if name not in VALID_PARAMETERS:
            raise ValueError(f"Invalid parameter: {name}")
        
        param_range = VALID_PARAMETERS[name]
        if isinstance(param_range, (list, set)):
            if value not in param_range:
                raise ValueError(f"Invalid value for {name}: {value}. Must be one of {param_range}")
        elif isinstance(param_range, tuple):
            min_val, max_val = param_range
            if not min_val <= value <= max_val:
                raise ValueError(f"Invalid value for {name}: {value}. Must be between {min_val} and {max_val}")
        elif param_range is None:
            if not isinstance(value, str):
                raise ValueError(f"Invalid value for {name}: {value}. Must be a string")
        else:
            raise ValueError(f"Invalid parameter range definition for {name}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}?name={name}&val={value}&type=set&time={self.utc_now()}", timeout=self.timeout) as response:
                    return (response.status == 200) and (await response.json() == {name: value})
        except aiohttp.ClientError as err:
            raise APIConnectionError("Timeout connecting to api") from err

    async def get_parameter(self, name: str) -> dict:
        """Get a parameter."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}?name={name}&val=0&type=get&time={self.utc_now()}", timeout=self.timeout) as response:
                    return await response.json()
        except aiohttp.ClientError as err:
            raise APIConnectionError("Timeout connecting to api") from err

class APIConnectionError(Exception):
    """Exception class for connection error."""