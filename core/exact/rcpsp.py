"""
rcpsp.py
--------
Implementazione del modello RCPSP classico (Resource-Constrained Project
Scheduling Problem) tramite CP-SAT (Constraint Programming + SAT).

Obiettivo: minimizzare il makespan, ovvero il tempo di inizio dell'attività
fittizia finale (n-1), la cui durata è 0.

Variabili decisionali:
    start[i]    — tempo di inizio dell'attività i
    interval[i] — variabile intervallo (lega start, durata, end)

Vincoli fondamentali:
    1. Precedenze finish-to-start: start[j] >= start[i] + durata[i] per ogni (i, j) in A_precedencesFS.
    2. Risorse rinnovabili: add_cumulative per ogni risorsa k.
    3. Attività fittizia iniziale fissata a t=0.
"""

from collections import defaultdict, deque
from ortools.sat.python import cp_model as cpm
from utils.validators.validate_input_rcpsp import validate_inputs
import time

class Model:
    """
    Modello CP-SAT per il problema RCPSP classico.

    Parametri
    ----------
    n : int
        Numero totale di attività incluse le due fittizie.
        Attività 0 = fittizia iniziale, attività n-1 = fittizia finale.
    durations : list[int]
        Vettore delle durate p. durations[0] = durations[n-1] = 0.
    precedences : list[tuple[int, int]]
        Lista di coppie (i, j): i deve completarsi prima che j inizi.
    resources : list[int]
        Vettore delle disponibilità R[k] per ciascuna delle m risorse.
    consumption : list[list[int]]
        Matrice r[i][k]: unità di risorsa k usate dall'attività i
        per ogni istante in cui è in esecuzione.
        consumption[0][k] = consumption[n-1][k] = 0 per ogni k.
    horizon : int
        Orizzonte temporale massimo D. Definisce il dominio delle variabili.
    validate_input : bool
        Se True esegue la validazione degli input prima di costruire il modello.
    """

    def __init__(
        self,
        n: int,
        durations: list[int],
        precedences: list[tuple[int, int]],
        resources: list[int],
        consumption: list[list[int]],
        horizon: int,
        validate_input: bool = True,
    ):
        self._n = n
        self._activities = list(range(n))
        self._durations = durations
        self._precedences = precedences
        self._resources = resources
        self._consumption = consumption
        self._horizon = horizon

        # Risultati (popolati da solve)
        self._start_times: dict[int, int] | None = None
        self._makespan: int | None = None
        self._status: int | None = None
        self._solutions: dict[str, int, int, int] | None = None

        if validate_input:
            validate_inputs(self)
        
    def _earliest_start(self): 
        """ 
        Calcola l'earliest start time per l'attività i, considerando i predecessori. 
        Riduce notevolmente il dominio delle variabili start[i]. 
        """ 
        graph = defaultdict(list) 
        indegree = [0]*self._n 
        
        for i, j in self._precedences: 
            graph[i].append(j) 
            indegree[j] += 1 
        
        ES = [0]*self._n 
        queue = deque([i for i in range(self._n) if indegree[i] == 0]) 
        
        while queue: 
            u = queue.popleft() 
            for v in graph[u]: 
                ES[v] = max(ES[v], ES[u] + self._durations[u]) 
                indegree[v] -= 1 
                if indegree[v] == 0: 
                    queue.append(v) 
        return ES
    
    def _latest_start(self, i: int):
        """
        Calcola il latest start time ammissibile per 
        l'attività i rispettando la deadline. Serve per 
        ridurre il dominio di start[i].
        """
        return self._horizon - self._durations[i]

    # ──────────────────────────────────────────────────────────────────────────
    # BUILD MODEL
    # ──────────────────────────────────────────────────────────────────────────

    def build_model(self) -> tuple[cpm.CpModel, dict[int, cpm.IntVar], int]:
        """
        Costruisce il modello CP-SAT e restituisce (model, start).

        Restituisce
        -----------
        model : cp_model.CpModel
            Modello pronto per essere passato al solver.
        start : dict[int, cp_model.IntVar]
            Variabili di inizio per ogni attività, utili per leggere
            la soluzione dopo la risoluzione.
        Cmax: int
            Makespan
        """
        model = cpm.CpModel()

        # Calcolo gli intervalli ammissibili nei quali una certa attività può essere completata
        ES = self._earliest_start()
        LS = {i: self._latest_start(i) for i in self._activities}

        # ── Variabili decisionali ─────────────────────────────────────────────
        start = {
            i: model.new_int_var(ES[i], LS[i], f"start_{i}")
            for i in self._activities
        }

        # NewIntervalVar lega internamente start, durata fissa e end:
        # end[i] = start[i] + durations[i] è già implicito.
        interval = {
            i: model.new_fixed_size_interval_var(
                start[i],
                self._durations[i],
                f"interval_{i}",
            )
            for i in self._activities
        }

        # Creo la variabile Cmax
        Cmax = model.new_int_var(0, self._horizon, "makespan")

        # ── Attività fittizia iniziale fissata a 0 ────────────────────────────
        model.add(start[0] == 0)

        # ── Vincolo l'attività fittizia ad essere ultima ──────────────────────
        last = self._n - 1

        for i in self._activities:
            if i != last:
                model.add(start[last] >= start[i] + self._durations[i])

        # ── Vincolo 1: precedenze finish-to-start ─────────────────────────────
        # start[j] >= end[i]  ⟺  start[j] >= start[i] + durations[i]
        for (i, j) in self._precedences:
            model.add(start[j] >= start[i] + self._durations[i])

        # ── Vincolo 2: risorse rinnovabili (add_cumulative) ────────────────────
        # Per ogni risorsa k, la somma dei consumi delle attività attive
        # in ogni istante non deve superare la disponibilità R[k].
        for k in range(len(self._resources)):
            intervals_k = []
            demands_k = []
            for i in self._activities:
                if self._consumption[i][k] > 0:
                    intervals_k.append(interval[i])
                    demands_k.append(self._consumption[i][k])
            if intervals_k:
                model.add_cumulative(intervals_k, demands_k, self._resources[k])

        # ── Vincolo 3: definizione del makespan Cmax ──────────────────────────
        for i in self._activities:
            model.add(Cmax >= start[i] + self._durations[i])

        # ── Obiettivo: minimizza il makespan ──────────────────────────────────
        model.minimize(Cmax)

        return model, start, Cmax

    # ──────────────────────────────────────────────────────────────────────────
    # SOLVE
    # ──────────────────────────────────────────────────────────────────────────

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
        model, start, Cmax= self.build_model()

        solver = cpm.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit
        solver.parameters.log_search_progress = verbose

        raw_status = solver.solve(model)
        self._status = raw_status

        if raw_status in (cpm.OPTIMAL, cpm.FEASIBLE):
            self._start_times = {
                i: solver.value(start[i]) for i in self._activities
            }
            self._makespan = solver.value(Cmax)
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

    # ──────────────────────────────────────────────────────────────────────────
    # OUTPUT
    # ──────────────────────────────────────────────────────────────────────────

    def get_schedule(self) -> list[dict]:
        """
        Restituisce la schedulazione come lista di dizionari ordinata per
        tempo di inizio. Richiede che solve() sia stato chiamato con successo.

        Ogni elemento ha le chiavi: activity, start, end, duration.
        """
        if self._start_times is None:
            raise RuntimeError(
                "Il modello non è ancora stato risolto. Chiamare solve() prima."
            )

        schedule = [
            {
                "activity": i,
                "start":    self._start_times[i],
                "end":      self._start_times[i] + self._durations[i],
                "duration": self._durations[i],
            }
            for i in self._activities
        ]

        return sorted(schedule, key=lambda r: r["start"])
    
    def get_final_solution(self):
        """
        Metodo da chiamare per costruire il modello,
        risolverlo e restituire la soluzione.
        """
        model, start, Cmax = self.build_model()
        start_time = time.time()
        status = self.solve()
        end_time = time.time()
        schedule = self.get_schedule()

        return {"solution": self.solutions, "start": self.start_times, 
                "Cmax": self.makespan, "schedule": schedule, 
                "elapsed_time": end_time - start_time}

    # ──────────────────────────────────────────────────────────────────────────
    # PROPERTIES
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def makespan(self) -> int | None:
        return self._makespan

    @property
    def status(self) -> int | None:
        return self._status

    @property
    def start_times(self) -> dict[int, int] | None:
        return self._start_times
    
    @property
    def solutions(self) -> dict[str, int, int, int] | None:
        return self._solutions

def test_modulo():
    import time
    """
    Metodo per testare il modulo quando eseguito. I dati di input sono inventati.
    """
    num_attività = 50
    durate = [
        0,
        3, 5, 2, 6, 4, 7, 3, 5, 6,
        4, 8, 3, 5, 7, 6, 2, 4, 5, 3,
        6, 4, 7, 3, 5, 6, 8, 4, 3, 5,
        7, 6, 2, 4, 5, 3, 6, 7, 7, 3,
        5, 6, 4, 8, 3, 5, 7, 4, 4,
        0
    ]
    precedenze = [
        (0,1),(0,2),(0,3),

        (1,4),(1,5),
        (2,6),(2,7),
        (3,8),(3,9),

        (4,10),(5,10),
        (6,11),(7,11),
        (8,12),(9,12),

        (10,13),(11,14),(12,15),

        (13,16),(13,17),
        (14,18),(14,19),
        (15,20),(15,21),

        (16,22),(17,22),
        (18,23),(19,23),
        (20,24),(21,24),

        (22,25),(23,26),(24,27),

        (25,28),(26,29),(27,30),

        (28,31),(29,32),(30,33),

        (31,34),(32,35),(33,36),

        (34,37),(35,38),(36,39),

        (37,40),(38,41),(39,42),

        (40,43),(41,44),(42,45),

        (43,46),(44,46),(45,47),

        (46,48),(47,48),

        (48,49)
    ]
    risorse = [10, 8, 6]
    consumo = [
        [0,0,0],
        [3,2,1],[4,1,2],[2,2,1],[5,3,2],[3,2,2],[6,4,2],[2,3,1],[4,2,2],[5,3,1],
        [3,3,2],[6,4,3],[2,2,1],[4,3,2],[5,3,3],[4,2,2],[2,1,1],[3,2,1],[4,3,2],[2,2,1],
        [5,3,2],[3,2,1],[6,4,3],[2,2,1],[4,3,2],[5,3,2],[6,4,3],[3,2,1],[2,1,1],[4,2,2],
        [5,3,2],[4,2,2],[2,1,1],[3,2,1],[4,3,2],[2,2,1],[5,3,2],[3,2,1],[6,4,3],[2,2,1],
        [4,3,2],[5,3,2],[3,2,1],[6,4,3],[2,2,1],[4,3,2],[5,3,2],[3,2,1],[5,3,1],
        [0,0,0]
    ]
    scadenza = 120

    all_activities = set(range(num_attività))
    successors = {i for (i, j) in precedenze}
    terminal = all_activities - successors - {num_attività - 1}

    for i in terminal:
        precedenze.append((i, num_attività - 1))

    modello = Model(num_attività, durate, precedenze, risorse, consumo, scadenza, validate_input=True)
    modello.build_model()
    start_time = time.time()
    status = modello.solve()
    end_time = time.time()
    schedula = modello.get_schedule()
    print(f"="*60)
    print(f"Il problema ha avuto esito: {status}")
    print(f"\nSoluzione trovata: {modello.makespan} giorni")
    print(f"-"*60)
    print(f"Il solver ha impiegato {end_time-start_time:.6f} secondi")
    print(f"-"*60)
    for task in schedula:
        print(task)
    print(f"="*60)

if __name__ == "__main__":
    test_modulo()