from pydantic import BaseModel
from typing import List


class Analysis(BaseModel):
    cause:str
    severity:str
    weather_risk:str
    medicine_usage:str
    precautions:List[str]
    recommendation:str

class DiseaseReport(BaseModel):
    disease:str
    confidence:float
    weather:dict
    medicine:str
    estimated_cost:str
    analysis:Analysis