import json
from app.models.ai_sessions import AISession

def save_report(db,report):
    print("Saving report...")
    print(report)
    session=db.query(AISession).first()
    if session:
        session.report=json.dumps(report)
    else:
        session=AISession(
            report=json.dumps(report),
            conversation='[]'
        )
        db.add(session)
    db.commit()
    print("report save successfully")
def load_report(db):
    session=db.query(AISession).first()
    if not session:
        return None
    return json.loads(session.report)

def save_conversation(db, conversation):

    import json

    session = db.query(AISession).first()

    if session:

        session.conversation = json.dumps(conversation)

        db.commit()

def load_conversation(db):

    import json

    session = db.query(AISession).first()

    if session and session.conversation:

        return json.loads(session.conversation)

    return []