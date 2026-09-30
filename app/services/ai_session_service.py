import json


def save_report(db, report):
    print("Saving report...")
    print(report)

    # Round-trip through JSON so only BSON-safe values are stored
    report = json.loads(json.dumps(report, default=str))

    db.ai_sessions.update_one(
        {},
        {
            "$set": {"report": report},
            "$setOnInsert": {"conversation": []}
        },
        upsert=True
    )

    print("report save successfully")


def load_report(db):
    session = db.ai_sessions.find_one()

    if not session:
        return None

    return session.get("report")


def save_conversation(db, conversation):
    db.ai_sessions.update_one(
        {},
        {"$set": {"conversation": conversation}}
    )


def load_conversation(db):
    session = db.ai_sessions.find_one()

    if session and session.get("conversation"):
        return session["conversation"]

    return []
