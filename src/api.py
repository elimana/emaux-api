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

    async def get_data(self) -> dict[str, Any]:
        """Get api data."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}?name=AllRd&val=0&type=get&time={self.utc_now()}", timeout=self.timeout) as response:
                    return await response.json()
        except aiohttp.ClientError as err:
            raise APIConnectionError("Timeout connecting to api") from err

    async def set_speed(self, speed: int) -> bool:
        """Set the pump speed."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}?name=SetCurrentSpeed&val={speed}&type=set&time={self.utc_now()}", timeout=self.timeout) as response:
                    _LOGGER.debug("Pump speed set to %s, status code: %s", speed, response.status)
                    return response.status == 200
        except aiohttp.ClientError as err:
            raise APIConnectionError("Timeout connecting to api") from err

    async def turn_on(self) -> bool:
        """Turn on the pump."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}?name=RunStop&val=1&type=set&time={self.utc_now()}", timeout=self.timeout) as response:
                    _LOGGER.debug("Pump turned on, status code: %s", response.status)
                    return response.status == 200
        except aiohttp.ClientError as err:
            raise APIConnectionError("Timeout connecting to api") from err

    async def turn_off(self) -> bool:
        """Turn off the pump."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}?name=RunStop&val=2&type=set&time={self.utc_now()}", timeout=self.timeout) as response:
                    _LOGGER.debug("Pump turned off, status code: %s", response.status)
                    return response.status == 200
        except aiohttp.ClientError as err:
            raise APIConnectionError("Timeout connecting to api") from err

    async def get_schedules(self) -> list[dict[str, Any]]:
        """Get the pump schedules."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}?name=AllWr&val=0&type=get&time={self.utc_now()}", timeout=self.timeout) as response:
                    return await response.json()
        except aiohttp.ClientError as err:
            raise APIConnectionError("Timeout connecting to api") from err

class APIConnectionError(Exception):
    """Exception class for connection error."""