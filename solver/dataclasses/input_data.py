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
    def validate_and_detect(self) -> 'InputData':
        # --- 1. VERIFICA DIMENSIONI ---
        if len(self.durations) != self.n:
            raise ValueError(f"La lunghezza di 'durations' ({len(self.durations)}) deve essere uguale a n ({self.n})")
        if self.release_dates is not None and len(self.release_dates) != self.n:
            raise ValueError(f"La lunghezza di 'release_dates' ({len(self.release_dates)}) deve essere uguale a n ({self.n})")
        if self.due_dates is not None and len(self.due_dates) != self.n:
            raise ValueError(f"La lunghezza di 'due_dates' ({len(self.due_dates)}) deve essere uguale a n ({self.n})")
        if len(self.consumption) != self.n:
            raise ValueError(f"La lunghezza di 'consumption' ({len(self.consumption)}) deve essere uguale a n ({self.n})")
        
        num_res = len(self.resources)
        for i, cons in enumerate(self.consumption):
            if len(cons) != num_res:
                raise ValueError(f"L'attività {i} ha {len(cons)} consumi, ma sono definite {num_res} risorse.")

        # --- 2. AUTO-RILEVAMENTO TIPO PROBLEMA ---
        
        # Rilevamento intervalli (has_intervals)
        if not self.has_intervals:
            has_tuple = any(isinstance(d, tuple) for d in self.durations) or \
                        any(isinstance(r, tuple) for r in self.resources)
            
            if not has_tuple and self.release_dates:
                has_tuple = any(isinstance(rd, tuple) for rd in self.release_dates if rd is not None)
            if not has_tuple and self.due_dates:
                has_tuple = any(isinstance(dd, tuple) for dd in self.due_dates if dd is not None)
                
            if has_tuple:
                self.has_intervals = True

        # Rilevamento RCPSP_MAX
        if not self.rcpsp_max:
            has_lags = any(len(p) > 2 for p in self.precedences)
            has_dates = False
            if self.release_dates:
                has_dates = any(rd is not None and (isinstance(rd, tuple) or (isinstance(rd, int) and rd > 0)) for rd in self.release_dates)
            if not has_dates and self.due_dates:
                # Se le date di scadenza sono diverse dall'orizzonte (e non None)
                has_dates = any(dd is not None and dd < self.horizon for dd in self.due_dates)
            
            if has_lags or has_dates or self.has_intervals:
                self.rcpsp_max = True

        return self