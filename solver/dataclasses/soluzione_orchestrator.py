from pydantic import BaseModel, Field, model_validator, AliasChoices
from typing import Dict, List, Optional, Any, Union

class SingleSolution(BaseModel):
    """Rappresenta una singola schedula trovata dal solver."""
    regola: Optional[str] = None
    
    # Supportiamo sia 'soluzione' che 'schedule' come nomi per la lista dei task
    soluzione: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        validation_alias=AliasChoices('soluzione', 'schedule')
    )
    
    # Supportiamo 'start_times' o 'schedule_dict' per il formato dizionario
    # Le chiavi possono essere int o str (es. {0: 0} o {"0": 0})
    schedule_dict: Optional[Dict[Union[int, str], Any]] = Field(
        default=None, 
        validation_alias=AliasChoices('schedule_dict', 'start')
    )
    
    durations: Optional[Any] = None
    makespan: int
    score: Optional[float] = None
    
    # Supportiamo sia 'penalità' che 'penalty'
    penalità: Optional[float] = Field(
        default=None, 
        validation_alias=AliasChoices('penalità', 'penalty')
    )
    
    rank_info: Optional[Dict[str, Any]] = None
    elapsed_time: Optional[float] = None

class BestSolutionsContainer(BaseModel):
    """Contenitore per la migliore soluzione e le top-k."""
    best: SingleSolution
    top_k_makespan: List[SingleSolution] = Field(default_factory=list)
    top_k_score: List[SingleSolution] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def handle_solver_output(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
            
        # Se i dati non hanno la chiave 'best', assumiamo che l'input sia 
        # la soluzione singola stessa (caso del modello esatto)
        if "best" not in data:
            return {
                "best": data,
                "top_k_makespan": [data],
                "top_k_score": []
            }
            
        # Normalizzazione delle liste None
        if data.get('top_k_makespan') is None:
            data['top_k_makespan'] = []
        if data.get('top_k_score') is None:
            data['top_k_score'] = []
            
        return data

class SoluzioneOrchestrator(BaseModel):
    """Output principale dell'orchestratore."""
    type: str
    problem_difficulty: str
    results: Optional[Dict[str, Any]] = None
    best: BestSolutionsContainer
