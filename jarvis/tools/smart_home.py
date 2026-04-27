"""
===========================================================
J.A.R.V.I.S. — Smart Home Tool
===========================================================
Home Assistant REST API + MQTT fallback.
===========================================================
"""

import logging
import requests
from jarvis.config import HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN

logger = logging.getLogger("jarvis.tools.smart_home")


class SmartHomeTool:
    """Control smart home devices via Home Assistant or MQTT."""

    def __init__(self, memory=None):
        self.memory = memory
        self._available = bool(HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN)
        if not self._available:
            logger.info("Smart home not configured — tool disabled")

    def execute(self, params: dict) -> str:
        if not self._available:
            return "Smart home not configured, Sir. Set HOME_ASSISTANT_URL and TOKEN in .env."
        action = params.get("action", "").lower()
        device = params.get("device", "")
        value = params.get("value", "")

        if action in ("turn_on", "on"):
            return self._call_service("turn_on", device)
        elif action in ("turn_off", "off"):
            return self._call_service("turn_off", device)
        elif action == "toggle":
            return self._call_service("toggle", device)
        elif action == "set":
            return self._set_value(device, value)
        elif action == "status":
            return self._get_status(device)
        elif action == "list":
            return self._list_devices()
        return f"Unknown smart home action: '{action}', Sir."

    def _call_service(self, service: str, entity_id: str) -> str:
        try:
            domain = entity_id.split(".")[0] if "." in entity_id else "light"
            resp = requests.post(
                f"{HOME_ASSISTANT_URL}/api/services/{domain}/{service}",
                headers={"Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}"},
                json={"entity_id": entity_id}, timeout=10
            )
            if resp.status_code == 200:
                return f"{entity_id} {service.replace('_',' ')} executed, Sir."
            return f"Smart home error: {resp.status_code}"
        except Exception as e:
            return f"Smart home command failed, Sir: {e}"

    def _set_value(self, entity_id: str, value: str) -> str:
        try:
            domain = entity_id.split(".")[0] if "." in entity_id else "climate"
            data = {"entity_id": entity_id}
            if domain == "climate":
                data["temperature"] = float(value)
                service = "set_temperature"
            elif domain == "light":
                data["brightness_pct"] = int(value)
                service = "turn_on"
            else:
                return f"Don't know how to set value for {domain}, Sir."
            resp = requests.post(
                f"{HOME_ASSISTANT_URL}/api/services/{domain}/{service}",
                headers={"Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}"},
                json=data, timeout=10
            )
            return f"Set {entity_id} to {value}, Sir." if resp.status_code == 200 else f"Error: {resp.status_code}"
        except Exception as e:
            return f"Failed to set value, Sir: {e}"

    def _get_status(self, entity_id: str) -> str:
        try:
            resp = requests.get(
                f"{HOME_ASSISTANT_URL}/api/states/{entity_id}",
                headers={"Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}"}, timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                return f"{entity_id}: {data.get('state', 'unknown')}"
            return f"Couldn't get status for {entity_id}, Sir."
        except Exception as e:
            return f"Status check failed, Sir: {e}"

    def _list_devices(self) -> str:
        try:
            resp = requests.get(
                f"{HOME_ASSISTANT_URL}/api/states",
                headers={"Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}"}, timeout=10
            )
            if resp.status_code == 200:
                devices = resp.json()
                lines = [f"Found {len(devices)} devices:\n"]
                for d in devices[:20]:
                    lines.append(f"  • {d['entity_id']}: {d['state']}")
                return "\n".join(lines)
            return "Couldn't list devices, Sir."
        except Exception as e:
            return f"Device listing failed, Sir: {e}"
