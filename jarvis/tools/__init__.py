"""
J.A.R.V.I.S. — Tools Package
Exports all tool modules for the orchestrator.
"""

from jarvis.tools.web_search import WebSearchTool
from jarvis.tools.weather import WeatherTool
from jarvis.tools.news import NewsTool
from jarvis.tools.system_control import SystemControlTool
from jarvis.tools.email_tool import EmailTool
from jarvis.tools.calendar_tool import CalendarTool
from jarvis.tools.music import MusicTool
from jarvis.tools.code_runner import CodeRunnerTool
from jarvis.tools.smart_home import SmartHomeTool
from jarvis.tools.proactive import ProactiveEngine

# Registry of all tools by name
TOOL_REGISTRY = {
    "web_search": WebSearchTool,
    "weather": WeatherTool,
    "news": NewsTool,
    "system_control": SystemControlTool,
    "email": EmailTool,
    "calendar": CalendarTool,
    "music": MusicTool,
    "code_runner": CodeRunnerTool,
    "smart_home": SmartHomeTool,
}

__all__ = [
    "WebSearchTool", "WeatherTool", "NewsTool", "SystemControlTool",
    "EmailTool", "CalendarTool", "MusicTool", "CodeRunnerTool",
    "SmartHomeTool", "ProactiveEngine", "TOOL_REGISTRY"
]
