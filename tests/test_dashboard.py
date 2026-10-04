from app.db import database


def test_dashboard_counts_use_the_keys_the_frontend_reads(client):
    db = database.get_database()

    db.predictions.insert_one({"id": 1, "disease": "Leaf spot"})
    db.predictions.insert_one({"id": 2, "disease": "Blight"})

    stats = client.get("/dashboard-stats").json()

    # HomePage.js reads exactly these four keys
    assert set(stats) == {"total_predictions", "total_equipment", "total_rentals", "total_users"}
    assert stats["total_predictions"] == 2
