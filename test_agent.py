from app.ai.agent.disease_agent import generate_disease_report

result = generate_disease_report(
    disease="Potato Late Blight",
    confidence=98.2,
    temperature=28,
    humidity=85
)

print(result)