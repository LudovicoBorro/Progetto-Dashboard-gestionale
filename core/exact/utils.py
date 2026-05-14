from ortools.sat.python import cp_model as cpm

# SOLVE

def solve(self, time_limit: int = 300, verbose: bool = False) -> str:
    """
    Risolve il modello e popola start_times, makespan e status.

    Parametri
    ----------
    time_limit : int
        Limite di tempo in secondi per il solver (default 300s).
    verbose : bool
        Se True mostra il log di ricerca del solver.

    Restituisce
    -----------
    status : str
        Stringa descrittiva dello stato: 'OPTIMAL', 'FEASIBLE',
        'INFEASIBLE' o 'UNKNOWN'.
    """
    model, start, cmax= self.build_model()

    solver = cpm.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8  # Parallelismo per velocizzare
    solver.parameters.log_search_progress = verbose

    raw_status = solver.solve(model)
    self._status = raw_status

    if raw_status in (cpm.OPTIMAL, cpm.FEASIBLE):
        self._start_times = {
            i: solver.value(start[i]) for i in self._activities
        }
        self._makespan = solver.value(cmax)
        value = int(solver.objective_value) 
        bound = int(solver.best_objective_bound)
        gap = value - bound
        self._solutions = {
            "status": solver.status_name(raw_status),
            "makespan": value,
            "best_bound": bound,
            "gap": gap
        }
    else:
        self._solutions = {
            "status": solver.status_name(raw_status),
            "makespan": None,
            "best_bound": None,
            "gap": None
        }

    return solver.status_name(raw_status)