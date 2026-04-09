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

        if validate_input:
            self._validate_inputs()

    # ──────────────────────────────────────────────────────────────────────────
    # VALIDATE INPUTS
    # ──────────────────────────────────────────────────────────────────────────

    def _validate_inputs(self):
        """
        Verifica la coerenza e ammissibilità degli input prima di costruire
        il modello. Rileva a priori le situazioni di inammissibilità strutturale
        evitando di avviare il solver su istanze non risolvibili.
        """
        m = len(self._resources)

        # ── Dimensione minima ─────────────────────────────────────────────────
        if self._n < 2:
            raise ValueError(
                "n deve essere almeno 2: sono richieste le due attività "
                "fittizie iniziale (0) e finale (n-1)."
            )

        # ── Coerenza dimensionale dei vettori ─────────────────────────────────
        if len(self._durations) != self._n:
            raise ValueError(
                f"durations ha {len(self._durations)} elementi, attesi {self._n}."
            )

        if len(self._consumption) != self._n:
            raise ValueError(
                f"consumption ha {len(self._consumption)} righe, attese {self._n}."
            )

        for i, row in enumerate(self._consumption):
            if len(row) != m:
                raise ValueError(
                    f"consumption[{i}] ha {len(row)} colonne, attese {m} "
                    f"(numero di risorse)."
                )

        # ── Valori non negativi sulle durate ──────────────────────────────────
        for i, d in enumerate(self._durations):
            if d < 0:
                raise ValueError(
                    f"durations[{i}] = {d}: le durate non possono essere negative."
                )

        # ── Disponibilità risorse strettamente positive ───────────────────────
        for k, r in enumerate(self._resources):
            if r <= 0:
                raise ValueError(
                    f"resources[{k}] = {r}: la disponibilità di ogni risorsa "
                    f"deve essere > 0."
                )

        # ── Consumo non negativo e non eccedente la capacità ─────────────────
        # Un consumo già superiore alla capacità rende l'attività
        # inschedulabile a prescindere — inammissibilità rilevabile a priori.
        for i in self._activities:
            for k, c in enumerate(self._consumption[i]):
                if c < 0:
                    raise ValueError(
                        f"consumption[{i}][{k}] = {c}: "
                        f"i consumi non possono essere negativi."
                    )
                if c > self._resources[k]:
                    raise ValueError(
                        f"consumption[{i}][{k}] = {c} supera la disponibilità "
                        f"della risorsa {k} = {self._resources[k]}: "
                        f"l'attività {i} non potrà mai essere schedulata."
                    )
        
        # ── Validazione su release_dates e due_dates ─────────────────────────
        if self._release_dates is not None and self._due_dates is not None:
            for i in self._activities:
                if self._release_dates[i] is not None and self._due_dates[i] is not None:
                    if self._release_dates[i] > self._due_dates[i] - self._durations[i]:
                        raise ValueError(
                            f"{self._release_dates[i]} non valida per l'attività {i}, "
                            f"non garantisce che la data di scadenza sia rispettata: "
                            f"l'attività {i} non potrà mai essere schedulata."
                        )

        # ── Attività fittizie ─────────────────────────────────────────────────
        if self._durations[0] != 0 or self._durations[self._n - 1] != 0:
            raise ValueError(
                "Le attività fittizie 0 e n-1 devono avere durata 0."
            )

        if any(self._consumption[0][k] != 0 for k in range(m)):
            raise ValueError(
                "L'attività fittizia iniziale (0) non deve consumare risorse."
            )

        if any(self._consumption[self._n - 1][k] != 0 for k in range(m)):
            raise ValueError(
                "L'attività fittizia finale (n-1) non deve consumare risorse."
            )

        # ── Deadline ──────────────────────────────────────────────────────────
        if self._horizon <= 0:
            raise ValueError(
                f"deadline = {self._horizon}: deve essere strettamente positiva."
            )

        # Lower bound banale: anche nel caso in cui tutte le attività si svolgessero 
        # in parallelo, il lower_bound è almeno uguale al massimo delle durate
        lower_bound = max(self._durations)
        if self._horizon < lower_bound:
            raise ValueError(
                f"deadline = {self._horizon} è inferiore alla durata massima "
                f"({lower_bound}): il problema è strutturalmente inammissibile."
            )
        
        # ── Validità degli archi di precedenza ───────────────────────────────
        valid_ids = set(self._activities)
        seen_edges = set()

        for idx, (i, j, min_lag, max_lag) in enumerate(self._precedences):

            # ── Indici validi ─────────────────────────────
            if i not in valid_ids or j not in valid_ids:
                raise ValueError(
                    f"Precedenza [{idx}] ({i} → {j}): indici fuori range."
                )

            # ── Auto-loop ────────────────────────────────
            if i == j:
                raise ValueError(
                    f"Precedenza [{idx}]: self-loop non ammesso ({i} → {j})."
                )

            # ── Dummy nodes ──────────────────────────────
            if j == 0:
                raise ValueError(
                    f"Precedenza [{idx}]: attività 0 non può essere successore."
                )

            if i == self._n - 1:
                raise ValueError(
                    f"Precedenza [{idx}]: attività finale non può essere predecessore."
                )

            # ── min_lag ─────────────────────────────────
            if min_lag is None:
                raise ValueError(
                    f"Precedenza [{idx}] ({i} → {j}): min_lag mancante."
                )

            # ── max_lag ─────────────────────────────────
            if max_lag is not None and max_lag < min_lag:
                raise ValueError(
                    f"Precedenza [{idx}] ({i} → {j}): max_lag < min_lag."
                )

            # ── duplicati ───────────────────────────────
            if (i, j) in seen_edges:
                raise ValueError(
                    f"Precedenza duplicata ({i} → {j})."
                )
            seen_edges.add((i, j))

        # ── Cicli nel grafo delle precedenze ─────────────────────────────────
        _check_time_feasibility(self._precedences, self._n)
        
        # ── Release e due date validation ────────────────────────────────────
        if self._release_dates is not None:
            if len(self._release_dates) != self._n:
                raise ValueError("release_dates dimensione errata")

        if self._due_dates is not None:
            if len(self._due_dates) != self._n:
                raise ValueError("due_dates dimensione errata")

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
        Cmax: int
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

        # Creo la variabile Cmax
        Cmax = model.new_int_var(0, self._horizon, "makespan")

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

        # ── Vincolo 3: definizione del makespan Cmax ──────────────────────────
        for i in self._activities:
            model.add(Cmax >= start[i] + self._durations[i])

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
        model, start, Cmax = self.build_model()

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
    
# ──────────────────────────────────────────────────────────────────────────────
# UTILITY — rilevamento cicli
# ──────────────────────────────────────────────────────────────────────────────
    
def _check_time_feasibility(precedences, n):
    """
    Verifica che i vincoli di tipo:
        start[j] ≥ start[i] + min_lag
        start[j] ≤ start[i] + max_lag
    siano consistenti.
    """

    # trasformiamo tutto in:
    # start[j] ≥ start[i] + w
    edges = []

    for (i, j, min_lag, max_lag) in precedences:
        edges.append((i, j, min_lag))
        if max_lag is not None:
            edges.append((j, i, -max_lag))

    dist = [0] * n

    # Bellman-Ford
    for _ in range(n):
        updated = False
        for u, v, w in edges:
            if dist[v] < dist[u] + w:
                dist[v] = dist[u] + w
                updated = True
        if not updated:
            return

    # se ancora aggiornabile → ciclo positivo
    raise ValueError(
        "Vincoli temporali inconsistenti (positive cycle nei time-lag)."
    )

def test_modulo():
    import time

    """
    Metodo per testare il modello RCPSP/Max.
    I dati sono generati artificialmente.
    """

    num_attività = 50

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
    precedenze = [
        (i, j, durate[i], None)   # FS classico
        for (i, j) in precedenze_base
    ]

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
    all_activities = set(range(num_attività))
    successors = {i for (i, _, _, _) in precedenze}
    terminal = all_activities - successors - {num_attività - 1}

    for i in terminal:
        precedenze.append((i, num_attività - 1, durate[i], None))

    # ── Release / Due dates (opzionali) ──────────────────────
    release_dates = [0] * num_attività
    due_dates = [None] * num_attività

    # esempio: vincolo reale
    release_dates[10] = 5
    due_dates[20] = 60

    # ── Creazione modello ───────────────────────────────────
    modello = Model(
        n=num_attività,
        durations=durate,
        resources=risorse,
        consumption=consumo,
        precedences=precedenze,
        horizon=horizon,
        release_dates=release_dates,
        due_dates=due_dates,
        validate_input=True
    )

    # ── Solve ───────────────────────────────────────────────
    start_time = time.time()
    status = modello.solve()
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