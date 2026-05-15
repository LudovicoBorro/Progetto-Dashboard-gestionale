from pydantic import BaseModel, Field, model_validator, AliasChoices
from typing import Dict, List, Optional, Any, Union, Literal


# =====================================================================
# SINGOLA SOLUZIONE
# =====================================================================

class SingleSolution(BaseModel):
    """
    Rappresenta una singola schedula trovata dal solver.
    """

    regola: Optional[str] = None

    # Compatibilità legacy:
    # - soluzione
    # - schedule
    soluzione: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        validation_alias=AliasChoices("soluzione", "schedule")
    )

    # Compatibilità legacy:
    # - schedule_dict
    # - start
    schedule_dict: Optional[Dict[Union[int, str], Any]] = Field(
        default=None,
        validation_alias=AliasChoices("schedule_dict", "start")
    )

    durations: Optional[Any] = None

    makespan: int

    score: Optional[float] = None

    # INTERNO: usa SEMPRE "penalty"
    penalty: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("penalty", "penalità")
    )

    rank_info: Optional[Dict[str, Any]] = None

    elapsed_time: Optional[float] = None


# =====================================================================
# CONTAINER RANKING
# =====================================================================

class RankingDTO(BaseModel):
    """
    Ranking delle soluzioni generate dal solver.
    """

    best_solution: SingleSolution

    top_k_makespan: List[SingleSolution] = Field(default_factory=list)

    top_k_score: List[SingleSolution] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any):

        if not isinstance(data, dict):
            return data

        # CASO:
        # arriva direttamente una soluzione singola
        if "best_solution" not in data and "best" not in data:

            return {
                "best_solution": data,
                "top_k_makespan": [data],
                "top_k_score": []
            }

        # Compatibilità legacy
        if "best" in data and "best_solution" not in data:
            data["best_solution"] = data.pop("best")

        data.setdefault("top_k_makespan", [])
        data.setdefault("top_k_score", [])

        return data


# =====================================================================
# DTO FINALE UNIFICATO
# =====================================================================

class SolutionDTO(BaseModel):
    """
    DTO unificato restituito dall'orchestrator.
    """

    solution_type: str = Field(..., alias="type")

    search_strategy: str = Field(default="direct_solver")

    problem_difficulty: str

    n_runs: int 

    problem_type: Literal["RCPSP", "RCPSP_MAX"]

    ranking: RankingDTO

    results: Optional[Any] = None

    additional_info: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_data(cls, data: Any):

        if not isinstance(data, dict):
            return data

        # Compatibilità legacy:
        # is_rcpsp_max -> problem_type
        if "problem_type" not in data:

            data["problem_type"] = (
                "RCPSP_MAX"
                if data.get("is_rcpsp_max")
                else "RCPSP"
            )

        # Compatibilità legacy:
        # best -> ranking
        if "best" in data and "ranking" not in data:
            data["ranking"] = data.pop("best")

        return data

    def to_dict(self) -> Dict[str, Any]:

        return self.model_dump(
            by_alias=True,
            exclude_none=True
        )