"""
sgs_engine_rcpsp.py
-------------
Implementazione del motore che schedula le attività in modo da rispettare i vincoli
di precedenza e di risorsa del problema RCPSP/Max.

Due approcci utilizzati:
    - Approccio seriale: considera l'attività come variabile di fase
    - Approccio parallelo: considera il tempo come variabile di fase

Entrambe gli approcci ricevono una lista di priorità determinata da regole
di priorità definite nei rispettivi moduli in priority_rules.

L'output standard è:
[
    {"activity": i, "start": t, "end": t + d}
]
"""

from utils.validators.validate_input_rcpsp_max import validate_inputs

class SGSEngine:

    def __init__(
            self,
            n: int,
            durations: list[int],
            precedences: list[tuple[int, int, int, int | None]],
            resources: list[int],
            consumption: list[list[int]],
            horizon: int,
            release_dates: list[int | None] | None,
            due_dates: list[int | None] | None,
            validate_input: True,
            ):
        self._n = n
        self._activities = list(range(n))
        self._durations = durations
        self._resources = resources
        self._consumption = consumption
        self._precedences = precedences
        self._horizon = horizon
        self._release_dates = release_dates
        self._due_dates = due_dates

        self._schedule_serial: list[dict[int, int, int]] | None = None
        self._makespan_serial: int | None = None
        self._schedule_parallel: list[dict[int, int, int]] | None = None
        self._makespan_parallel: int | None = None

        if validate_input:
            validate_inputs(self)

    def serial(self, priority_list):
        pass

    def parallel(self, priority_list):
        pass