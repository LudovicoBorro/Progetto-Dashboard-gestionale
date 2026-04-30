from pydantic import BaseModel

class SoluzioneOrchestrator(BaseModel):
    type: str
    problem_difficulty: str
    results: dict | None
    best: dict
