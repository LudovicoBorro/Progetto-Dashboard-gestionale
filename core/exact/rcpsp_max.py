"""
rcpsp_max.py
------------
Implementazione del modello RCPSP/Max (Resource-Constrained Project
Scheduling Problem) tramite CP-SAT (Constraint Programming + SAT).

Obiettivo: minimizzare il makespan, ovvero il tempo di inizio dell'attività
fittizia finale (n-1), la cui durata è 0.

Variabili decisionali:
    start[i]    — tempo di inizio dell'attività i
    interval[i] — variabile intervallo (lega start, durata, end)

Vincoli fondamentali:
    1. Precedenze generalizzate (time-lag constraints):
       Tutti i vincoli tra attività sono espressi nella forma unificata:
            start[j] ≥ start[i] + δ(i,j)
       dove δ(i,j) rappresenta il time-lag minimo tra l'inizio di i e j.
       Questa formulazione consente di rappresentare:
            - Finish-to-Start (FS): δ(i,j) = durata[i] + lag
            - Start-to-Start  (SS): δ(i,j) = lag
            - Finish-to-Finish (FF): δ(i,j) = durata[i] - durata[j] + lag
            - Start-to-Finish (SF): δ(i,j) = -durata[j] + lag
    2. Risorse rinnovabili: add_cumulative per ogni risorsa k.
    3. Attività fittizia iniziale fissata a t=0.
    7. Time-lag minimi e massimi:
       È possibile imporre anche vincoli superiori tra attività: start[j] ≤ start[i] + Δ(i,j)
       consentendo di modellare intervalli temporali completi tra attività.
    8. Release dates (date di disponibilità):
       Ogni attività può avere un tempo minimo di inizio: start[i] ≥ r[i]
    9. Due dates / deadlines per attività:
       Ogni attività può avere un tempo massimo di completamento: start[i] + durata[i] ≤ d[i]
"""

from collections import defaultdict, deque
from ortools.sat.python import cp_model as cpm
from utils.validators.validate_input_rcpsp_max import validate_inputs
from core.exact.utils import solve
import random, time

class Model:
    """
    Modello CP-SAT per RCPSP/Max.

    Parametri
    ---------
    n : int
        Numero totale di attività incluse le due fittizie.
        Attività 0 = fittizia iniziale, attività n-1 = fittizia finale.
    durations : list[int]
        Vettore delle durate p. durations[0] = durations[n-1] = 0.
    resources : list[int]
        Vettore delle disponibilità R[k] per ciascuna delle m risorse.
    consumption : list[list[int]]
        Matrice r[i][k]: unità di risorsa k usate dall'attività i
        per ogni istante in cui è in esecuzione.
        consumption[0][k] = consumption[n-1][k] = 0 per ogni k.
    precedences : list[tuple[int, int, int, int | None]]
        Lista dei vincoli di precedenza generalizzati nella forma:
            (i, j, min_lag, max_lag)
        che rappresentano:
            min_lag ≤ start[j] - start[i] ≤ max_lag
        dove:
            - min_lag = δ(i,j) è il time-lag minimo
            - max_lag è opzionale (None se non presente)
        Questa formulazione unificata permette di rappresentare:
            - FS, SS, FF, SF
            - vincoli con lag minimo e massimo
    horizon : int
        Orizzonte temporale superiore per il dominio delle variabili.
    release_dates : list[int] | None
        Vettore r[i]: tempo minimo di inizio per ogni attività.
        Se None, nessun vincolo di rilascio è applicato.
    due_dates : list[int] | None
        Vettore d[i]: tempo massimo di completamento per ogni attività.
        Se None, nessun vincolo di deadline è applicato.
    validate_input : bool
        Se True esegue la validazione degli input prima di costruire il modello.
    """

    def __init__(
        self,
        n: int, 
        durations: list[int],
        resources: list[int],
        consumption: list[list[int]],
        precedences: list[tuple[int, int, int, int | None]],
        horizon: int,
        release_dates: list[int | None] | None,
        due_dates: list[int | None] | None,
        validate_input : bool = True
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

        # Risultati (popolati da solve)
        self._start_times: dict[int, int] | None = None
        self._makespan: int | None = None
        self._status: int | None = None
        self._solutions: dict[str, int, int, int] | None = None

        if validate_input:
            validate_inputs(self)

    # ──────────────────────────────────────────────────────────────────────────
    # RIDUZIONE DOMINIO VARIABILI
    # ──────────────────────────────────────────────────────────────────────────

    def _earliest_start(self):
        """
        Calcola gli earliest start ES[i] considerando:
        - precedenze generalizzate (min_lag)
        - release dates

        Risolve un longest path su grafo aciclico.
        """
        graph = defaultdict(list)
        indegree = [0] * self._n

        # costruzione grafo con pesi = min_lag
        for (i, j, min_lag, _) in self._precedences:
            graph[i].append((j, min_lag))
            indegree[j] += 1

        # inizializzazione
        ES = [0] * self._n

        # release dates
        if self._release_dates is not None:
            for i in range(self._n):
                if self._release_dates[i] is not None:
                    ES[i] = max(ES[i], self._release_dates[i])

        # topological order (Kahn)
        queue = deque([i for i in range(self._n) if indegree[i] == 0])

        while queue:
            u = queue.popleft()
            for v, lag in graph[u]:
                ES[v] = max(ES[v], ES[u] + lag)
                indegree[v] -= 1
                if indegree[v] == 0:
                    queue.append(v)

        return ES
    
    def _latest_start(self):
        """
        Calcola LS[i] considerando:
        - horizon
        - due dates
        - max_lag (se presenti)

        Backward pass su grafo.
        """
        graph = defaultdict(list)

        # grafo inverso per backward
        for (i, j, _, max_lag) in self._precedences:
            if max_lag is not None:
                graph[j].append((i, max_lag))

        # inizializzazione
        LS = [self._horizon - self._durations[i] for i in range(self._n)]

        # due dates
        if self._due_dates is not None:
            for i in range(self._n):
                if self._due_dates[i] is not None:
                    LS[i] = min(LS[i], self._due_dates[i] - self._durations[i])

        # backward relaxation (tipo Bellman-Ford light)
        updated = True
        while updated:
            updated = False
            for j in range(self._n):
                for i, max_lag in graph[j]:
                    if LS[i] > LS[j] + max_lag:
                        LS[i] = LS[j] + max_lag
                        updated = True

        return LS

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
        cmax: int
            Makespan
        """
        model = cpm.CpModel()

        # Calcolo degli intervalli ammissibili
        ES = self._earliest_start()
        LS = self._latest_start()

        for i in range(self._n):
            if ES[i] > LS[i]:
                raise ValueError(
                    f"Attività {i} infeasible: ES={ES[i]} > LS={LS[i]}"
                )

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

        # Creo la variabile cmax
        cmax = model.new_int_var(0, self._horizon, "makespan")

        # ── Attività fittizia iniziale fissata a 0 ────────────────────────────
        model.add(start[0] == 0)

        # ── Vincolo l'attività fittizia ad essere ultima ──────────────────────
        last = self._n - 1

        for i in self._activities:
            if i != last:
                model.add(start[last] >= start[i] + self._durations[i])

        # ── Vincolo 1: precedenze generalizzate ───────────────────────────────
        # start[j] ≥ start[i] + δ(i,j)
        for (i, j, min_lag, max_lag) in self._precedences:
            model.add(start[j] >= start[i] + min_lag)
            if max_lag is not None:
                model.add(start[j] - start[i] <= max_lag)

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

        # ── Vincolo 3: definizione del makespan cmax ──────────────────────────
        for i in self._activities:
            model.add(cmax >= start[i] + self._durations[i])

        # ── Vincolo 4: eventuali release_dates ────────────────────────────────
        if self._release_dates is not None:
            for i in self._activities:
                if self._release_dates[i] is not None:
                    model.add(start[i] >= self._release_dates[i])

        # ── Vincolo 5: eventuali due_dates ────────────────────────────────────
        if self._due_dates is not None:
            for i in self._activities:
                if self._due_dates[i] is not None:
                    model.add(start[i] + self._durations[i] <=  self._due_dates[i])

        # ── Obiettivo: minimizza il makespan ──────────────────────────────────
        model.minimize(cmax)

        return model, start, cmax
    

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
        self.build_model()
        start_time = time.time()
        solve(self)
        end_time = time.time()
        schedule = self.get_schedule()

        return {"solution": self.solutions, "start": self.start_times, 
                "makespan": self.makespan, "schedule": schedule, 
                "elapsed_time": end_time - start_time}
    

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
    Metodo per testare il modello RCPSP/Max.
    I dati sono generati artificialmente.
    """

    num_attivita = 50

    # ── Durate ───────────────────────────────────────────────
    durate = [
        0,
        3, 5, 2, 6, 4, 7, 3, 5, 6,
        4, 8, 3, 5, 7, 6, 2, 4, 5, 3,
        6, 4, 7, 3, 5, 6, 8, 4, 3, 5,
        7, 6, 2, 4, 5, 3, 6, 4, 7, 3,
        5, 6, 4, 8, 3, 5, 7, 4, 4,
        0
    ]

    # ── Precedenze (convertite in RCPSP/Max) ─────────────────
    # FS con lag = 0 → min_lag = durata[i]
    precedenze_base = [
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

    # Conversione in (i, j, min_lag, max_lag)
    precedenze = []
    for (i, j) in precedenze_base:
        if random.random() > 0.85:
            max_lag = durate[i] + int(random.random() * durate[i] // 3)
        else:
            max_lag = None
        precedenze.append((i, j, durate[i], max_lag))

    # ── Risorse ──────────────────────────────────────────────
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

    # ── Horizon ──────────────────────────────────────────────
    horizon = 120

    # ── Collegamento automatico al nodo finale ───────────────
    all_activities = set(range(num_attivita))
    successors = {i for (i, _, _, _) in precedenze}
    terminal = all_activities - successors - {num_attivita - 1}

    for i in terminal:
        precedenze.append((i, num_attivita - 1, durate[i], None))

    # ── Release / Due dates (opzionali) ──────────────────────
    release_dates = [0] * num_attivita
    due_dates = [None] * num_attivita

    # esempio: vincolo reale
    release_dates[10] = 5
    due_dates[20] = 60

    # ── Creazione modello ───────────────────────────────────
    modello = Model(
        n=num_attivita,
        durations=durate,
        resources=risorse,
        consumption=consumo,
        precedences=precedenze,
        horizon=horizon,
        release_dates=release_dates,
        due_dates=due_dates,
        validate_input=True
    )

    modello.build_model()

    # ── Solve ───────────────────────────────────────────────
    start_time = time.time()
    status = solve(modello)
    end_time = time.time()

    schedula = modello.get_schedule()

    # ── Output ──────────────────────────────────────────────
    print("=" * 60)
    print(f"Status: {status}")
    print(f"Makespan: {modello.makespan}")
    print("-" * 60)
    print(f"Tempo solver: {end_time - start_time:.6f} sec")
    print("-" * 60)

    for task in schedula:
        print(task)

    print("=" * 60)

if __name__ == "__main__":
    test_modulo()