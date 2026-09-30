from app.db.database import get_database


def execute():

    equipment = get_database().equipment.find(
        {"availability": "Available"}
    )

    return [
        {
            "name": item["equipment_name"],
            "owner": item["owner_name"],
            "location": item["location"],
            "price": item["price_per_day"]
        }
        for item in equipment
    ]
