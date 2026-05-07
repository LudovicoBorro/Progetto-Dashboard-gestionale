from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Tuple, Union

class BaseDataBAndB(BaseModel):
    n: int = Field(ge=2, description="Numero totale di attività (incluse dummy)")
    durations: List[Union[int, Tuple[int, int]]]
    precedences: List[Tuple[int, int, str, int, Optional[int]]]
    resources: List[Union[int, Tuple[int, int]]]
    horizon: int = Field(ge=0)
    release_dates: List[Union[int, None, Tuple[int, int]]]
    due_dates: List[Union[int, None, Tuple[int, int]]]
    consumption: List[List[int]]

    @model_validator(mode="after")
    def check_dimensions(self) -> 'BaseDataBAndB':
        if len(self.durations) != self.n:
            raise ValueError(f"La lunghezza di 'durations' ({len(self.durations)}) deve essere uguale a n ({self.n})")
        if len(self.release_dates) != self.n:
            raise ValueError(f"La lunghezza di 'release_dates' ({len(self.release_dates)}) deve essere uguale a n ({self.n})")
        if len(self.due_dates) != self.n:
            raise ValueError(f"La lunghezza di 'due_dates' ({len(self.due_dates)}) deve essere uguale a n ({self.n})")
        if len(self.consumption) != self.n:
            raise ValueError(f"La lunghezza di 'consumption' ({len(self.consumption)}) deve essere uguale a n ({self.n})")
        
        # Verifica dimensioni matrice consumi
        num_res = len(self.resources)
        for i, cons in enumerate(self.consumption):
            if len(cons) != num_res:
                raise ValueError(f"L'attività {i} ha {len(cons)} consumi, ma sono definite {num_res} risorse.")
        
        return self