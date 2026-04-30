from pydantic import BaseModel
from solver.dataclasses.best_config_b_and_b import BestConfigBAndB
from solver.dataclasses.soluzione_orchestrator import SoluzioneOrchestrator

class BestSolutionBAndB(BaseModel):
    config: BestConfigBAndB
    solution: SoluzioneOrchestrator