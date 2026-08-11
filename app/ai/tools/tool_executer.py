from app.ai.tools.weather_tool import execute as weather_tool
from app.ai.tools.price_tool import execute as price_tool
from app.ai.tools.equipment_tool import execute as equipment_tool
from app.ai.tools.history_tool import execute as history_tool


def execute_tool(plan):

    tool = plan["tool"]

    if tool == "weather":

        city = plan.get("city")

        if city:
            return weather_tool(city)

        return {"error": "City not provided"}

    elif tool == "price":

        crop = plan.get("crop")

        if crop:
            return price_tool(crop)

        return {"error": "Crop not provided"}

    elif tool == "equipment":

        return equipment_tool()

    elif tool == "history":

        return history_tool()

    return None