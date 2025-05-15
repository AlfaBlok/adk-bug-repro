import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
import time

def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city for which to retrieve the weather report.

    Returns:
        dict: status and result or error msg.
    """
    if city.lower() == "new york":
        # time.sleep(1) # Temporarily remove sleep completely
        return {
            "status": "success",
            "report": (
                "The weather in New York is sunny with a temperature of 25 degrees"
                " Celsius (77 degrees Fahrenheit)."
            ),
        }
    else:
        return {
            "status": "error",
            "error_message": f"Weather information for '{city}' is not available.",
        }


def slow_get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city, with an artificial delay.

    Args:
        city (str): The name of the city for which to retrieve the weather report.

    Returns:
        dict: status and result or error msg.
    """
    if city.lower() == "new york":
        # print(f"--- slow_get_weather TOOL: Simulating 5 second delay for {city} ---")
        time.sleep(5)
        # print(f"--- slow_get_weather TOOL: Delay finished for {city} ---")
        return {
            "status": "success",
            "report": (
                "(Slowly) The weather in New York is sunny with a temperature of 25 degrees"
                " Celsius (77 degrees Fahrenheit)."
            ),
        }
    else:
        return {
            "status": "error",
            "error_message": f"Slow weather information for '{city}' is not available.",
        }


def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.

    Returns:
        dict: status and result or error msg.
    """

    if city.lower() == "new york":
        tz_identifier = "America/New_York"
    else:
        return {
            "status": "error",
            "error_message": (
                f"Sorry, I don't have timezone information for {city}."
            ),
        }

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = (
        f'The current time in {city} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
    )
    return {"status": "success", "report": report}


root_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.0-flash",
    description=(
        "Agent to answer questions about the time and weather in a city. Can also get weather slowly."
    ),
    instruction=(
        """You are a helpful agent who can answer user questions about the time and weather in a city.
        You have two tools for weather: get_weather (fast) and slow_get_weather (slow).
        IMPORTANT: before calling the slow weather app, inform the user BEFORE making the call (don't ask permission, just inform). 
        Once the slow weather tool has run inform the user again.
        Use slow weather if user asks for it. 
        Otherwise never use it, and no need to inform the user about it. 
        Thank you agent for your service."""
    ),
    tools=[get_weather, slow_get_weather, get_current_time],
)