from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Tuple, Union

class InputData(BaseModel):
    n: int = Field(ge=0, description="Numero totale di attività")
    durations: List[Union[int, Tuple[int, int]]]
    precedences: List[Union[Tuple[int,int], Tuple[int, int, str, int, Optional[int]]]]
    resources: List[Union[int, Tuple[int, int]]]
    horizon: int = Field(ge=0)
    release_dates: Optional[List[Union[int, None, Tuple[int, int]]]] = None
    due_dates: Optional[List[Union[int, None, Tuple[int, int]]]] = None
    consumption: List[List[int]]
    
    # Nomi opzionali per reporting
    activity_names: Optional[List[str]] = None
    resource_names: Optional[List[str]] = None

    # Configurazione Solver (pesi funzione obiettivo e limiti)
    top_k: int = Field(default=5, ge=1)
    time_weight: float = Field(default=1.0, ge=0.0, le=5.0, description="Peso assegnato al tempo di completamento del task nel calcolo del costo totale in caso di schedulazione non ammissibile")
    resource_weight: float = Field(default=1.0, ge=0.0, le=5.0, description="Peso assegnato all'utilizzo delle risorse nel calcolo del costo totale in caso di schedulazione non ammissibile")
    priority_weight: float = Field(default=1.0, ge=0.0, le=5.0, description="Peso assegnato alla priorità delle attività nel calcolo del costo totale in caso di schedulazione non ammissibile")
    tardiness_weight: float = Field(default=1.0, ge=0.0, le=5.0, description="Peso assegnato al ritardo nel calcolo del costo totale in caso di schedulazione non ammissibile")
    limit_lookahead: int = Field(default=5, ge=1, description="Il numero di task da considerare nel calcolo del costo totale in caso di schedulazione non ammissibile")
    instant_sol: bool = Field(default=False, description="Se True, viene generata una soluzione istantanea")
    priority_rule: Optional[str] = Field(default=None, description="Regola di priorità")
    rcpsp_max: bool = Field(default=False, description="Se True, viene generato un problema RCPSP/MAX")
    has_intervals: bool = Field(default=False, description="Se True, il problema ha intervalli e viene utilizzato il Branch and Bound euristico")
    max_nodes: int = Field(default=5000, ge=1, description="Numero massimo di nodi da esplorare nel Branch and Bound euristico")
    max_time: int = Field(default=600, ge=1, description="Tempo massimo di esecuzione in secondi per il Branch and Bound euristico")

    @model_validator(mode="after")
    def check_dimensions(self) -> 'InputData':
        if len(self.durations) != self.n:
            raise ValueError(f"La lunghezza di 'durations' ({len(self.durations)}) deve essere uguale a n ({self.n})")
        if self.release_dates is not None and len(self.release_dates) != self.n:
            raise ValueError(f"La lunghezza di 'release_dates' ({len(self.release_dates)}) deve essere uguale a n ({self.n})")
        if self.due_dates is not None and len(self.due_dates) != self.n:
            raise ValueError(f"La lunghezza di 'due_dates' ({len(self.due_dates)}) deve essere uguale a n ({self.n})")
        if len(self.consumption) != self.n:
            raise ValueError(f"La lunghezza di 'consumption' ({len(self.consumption)}) deve essere uguale a n ({self.n})")
        if self.limit_lookahead > self.n:
            raise ValueError(f"Il limit_lookahead ({self.limit_lookahead}) deve essere minore o uguale a n ({self.n})")
        # Verifica nomi attività
        if self.activity_names is not None and len(self.activity_names) != self.n:
            raise ValueError(f"La lunghezza di 'activity_names' ({len(self.activity_names)}) deve essere uguale a n ({self.n})")
        
        # Verifica dimensioni matrice consumi e nomi risorse
        num_res = len(self.resources)
        if self.resource_names is not None and len(self.resource_names) != num_res:
            raise ValueError(f"La lunghezza di 'resource_names' ({len(self.resource_names)}) deve essere uguale al numero di risorse ({num_res})")
            
        for i, cons in enumerate(self.consumption):
            if len(cons) != num_res:
                raise ValueError(f"L'attività {i} ha {len(cons)} consumi, ma sono definite {num_res} risorse.")
        
        return self