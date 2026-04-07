"""
rcpsp.py
--------
Implementazione del modello RCPSP classico (Resource-Constrained Project Scheduling Problem),
tramite programmazione lineare intera mista (MILP).

Il modello ha come obiettivo la minimizzazione della durata totale del progetto,
il cosiddetto makespan, cioè il tempo di completamento dell'ultima attività.

Variabile decisionale:
  x[i][t] ∈ {0, 1} — vale 1 se l'attività i inizia al tempo t.

I vincoli fondamentali per questo modello sono:
- Vincoli di precedenza finish-to-start.
- Vincoli di risorsa: in ogni istante t, il consumo totale di ogni risorsa non supera
  la disponibilità Rk.
- Ogni attivià inizia esattamente una volta.
- Il makespan è il tempo di completamento dell'attività fittizia finale.
"""

import pulp

class Model():
    """
    Modello MILP per il problema RCPSP classico.

    Parametri
    ----------
    n : int
        Numero totale di attività, incluse le due fittizie (0-indexed: 0..n-1).
        Le attività 0 e n-1 sono fittizie (inizio e fine progetto).
    durations : list[int]
        Vettore p delle durate. durations[0] = durations[n-1] = 0.
    precedences : list[tuple[int, int]]
        Lista di coppie (i, j) che indicano che i deve completarsi
        prima che j inizi (vincolo FSij min 0).
    resources : list[int]
        Vettore R di disponibilità per ciascuna delle m risorse rinnovabili.
        resources[k] = disponibilità della risorsa k per ogni istante.
    consumption : list[list[int]]
        Matrice r[i][k]: quantità di risorsa k usata dall'attività i
        per ogni istante in cui è in esecuzione.
        consumption[0][k] = consumption[n-1][k] = 0 per ogni k.
    deadline : int
        Orizzonte temporale massimo D del progetto. Definisce il dominio
        delle variabili x[i][t] (t = 0, 1, ..., D).
    """

    def __init__(
        self,
        n: int,
        durations: list[int],
        precedences: list[tuple[int, int]],
        resources: list[int],
        consumption: list[list[int]],
        deadline: int,
        validate_input: bool = True,
        ):
        
        self._n = n
        self._activities = list(range(n))
        self._durations = durations
        self._precedences = precedences
        self._m = len(resources)
        self._resources = resources
        self._consumption = consumption
        self._deadline = deadline
        self._time_horizon = list(range(deadline + 1))
        self._start_times: dict[int, int] | None = None
        self._makespan: int | None = None
        self._status: str | None = None
        if validate_input:
            self._validate_inputs()

    def _validate_inputs(self):
        if len(self._durations) != self._n:
            raise ValueError(f"durations deve avere lunghezza {len(self._n)}")

        if len(self._consumption) != self._n:
            raise ValueError(f"consumption deve avere {len(self._n)} righe (una per attività)")

        if any(len(row) != len(self._resources) for row in self._consumption):
            raise ValueError(f"Ogni riga di consumption deve avere lunghezza {self._m}")
        
        if any(d < 0 for d in self._durations):
            raise ValueError("Durate negative non ammesse")

        if any(r < 0 for r in self._resources):
            raise ValueError("Capacità risorse negative non ammesse")

        for i in range(self._n):
            for k in range(len(self._resources)):
                if self._consumption[i][k] < 0:
                    raise ValueError(f"Consumo negativo per attività {i}, risorsa {k}")
        
        if self._durations[0] != 0 or self._durations[self._n-1] != 0:
            raise ValueError("Le attività fittizie 0 e n-1 devono avere durata 0")

        for k in range(len(self._resources)):
            if self._consumption[0][k] != 0 or self._consumption[self._n-1][k] != 0:
                raise ValueError("Le attività fittizie non devono consumare risorse")
            
        for (i, j) in self._precedences:
            if i < 0 or i >= self._n or j < 0 or j >= self._n:
                raise ValueError(f"Precedenza non valida: ({i}, {j}) fuori range")

            if i == j:
                raise ValueError(f"Loop su attività {i}")

        if self._deadline <= 0:
            raise ValueError("Deadline deve essere positiva")

        if self._deadline < max(self._durations):
            raise ValueError("Deadline troppo piccola rispetto alle durate")
        
        for i in range(self._n):
            for k in range(len(self._resources)):
                if self._consumption[i][k] > self._resources[k]:
                    raise ValueError(
                        f"Attività {i} richiede più risorsa {k} della capacità disponibile"
                    )
        
        if has_cycle(self._n, self._precedences):
            raise ValueError("Il grafo delle precedenze contiene un ciclo")
                
    def _earliest_start(self, i: int):
        """
        Calcola l'earliest start time per l'attività i,
        considerando i predecessori. Riduce notevolmente
        il dominio delle variabili x[i][t].
        """
        if i == 0:
            return 0
        preds = [j for (j, k) in self._precedences if k == i]
        if not preds:
            return 0
        return max(self._earliest_start(j) + self._durations[j] for j in preds)
    
    def _latest_start(self, i: int):
        """
        Calcola il latest start time ammissibile per 
        l'attività i rispettando la deadline. Serve per 
        ridurre il dominio di x[i][t].
        """
        return self._deadline - self._durations[i]
    
    def build_model(self):
        """
        Costruisce il modello MILP e restituisce (prob, x).

        Restituisce
        -----------
        prob : pulp.LpProblem
            Il problema di ottimizzazione pronto per essere risolto.
        x : dict[int, dict[int, pulp.LpVariable]]
            Variabili binarie x[i][t].
        """
        prob = pulp.LpProblem("RCPSP", pulp.LpMinimize)

        # —— Dominio ridotto per ogni attività ————————————————————————————————
        # ES[i] e LS[i] restringono gli istanti t ammissibili per x[i][t],
        # riducendo il numero di variabili senza perdere l'ottimalità.
        ES = {i: self._earliest_start(i) for i in self._activities}
        LS = {i: self._latest_start(i) for i in self._activities}

        # —— Variabili decisionali ————————————————————————————————————————————
        # x[i][t] = 1 se l'attività i inizia all'istante t
        x = {
            i: {
                t: pulp.LpVariable(f"x_{i}_{t}", cat="Binary")
                for t in range(ES[i], LS[i] + 1)
            }
            for i in self._activities
        }
        
        # Fisso l'attività iniziale a t = 0
        prob += pulp.lpSum(t * x[0][t] for t in x[0]) == 0, "Inizia_a_zero"

        # ── Funzione obiettivo ───────────────────────────────────────────────
        # Minimizza il tempo di inizio dell'attività fittizia finale (n-1),
        # che coincide con il makespan (poiché la sua durata è 0).
        last = self._n - 1
        prob += pulp.lpSum(
            t * x[last][t] for t in x[last]
        ), "Minimizza_Makespan"

        # ── Vincolo 1: ogni attività inizia esattamente una volta ────────────
        for i in self._activities:
            prob += (
                pulp.lpSum(x[i][t] for t in x[i]) == 1,
                f"Inizia_una_sola_volta_{i}",
            )

        # ── Vincolo 2: precedenze finish-to-start ────────────────────────────
        # Se (i, j) ∈ A, allora S_j >= S_i + p_i, dove A = precedences
        # Formulato come: Σ_t t·x[j][t] >= Σ_t t·x[i][t] + p_i
        for (i, j) in self._precedences:
            prob += (
                pulp.lpSum(t * x[j][t] for t in x[j])
                >= pulp.lpSum(t * x[i][t] for t in x[i]) + self._durations[i],
                f"Precedenza_{i}_{j}",
            )

        # ── Vincolo 3: capacità delle risorse ────────────────────────────────
        # Per ogni istante t e ogni risorsa k:
        # Σ_i r[i][k] · Σ_{t'=t-p_i+1}^{t} x[i][t'] <= R[k]
        #
        # Il termine interno seleziona le attività in esecuzione in t,
        # cioè quelle iniziate in uno degli ultimi p_i istanti.
        for t in self._time_horizon:
            for k in range(self._m):
                in_execution = []
                for i in self._activities:
                    if self._consumption[i][k] == 0:
                        continue
                    pi = self._durations[i]
                    # L'attività i è attiva in t se è partita in [t-pi+1, t]
                    active_starts = [
                        x[i][s]
                        for s in range(max(ES[i], t - pi + 1), min(LS[i], t) + 1)
                        if s in x[i]
                    ]
                    if active_starts:
                        in_execution.append(
                            self._consumption[i][k] * pulp.lpSum(active_starts)
                        )
                if in_execution:
                    prob += (
                        pulp.lpSum(in_execution) <= self._resources[k],
                        f"Resource_{k}_t{t}",
                    )
        return prob, x
    
    def solve(self, solver=None, time_limit: int = 300, verbose: bool = False):
        """
        Risolve il modello e popola self.start_times, self.makespan e self.status.

        Parametri
        ----------
        solver : pulp.LpSolver | None
            Solver da utilizzare. Se None usa CBC (default PuLP).
        time_limit : int
            Limite di tempo in secondi per il solver (default 300s).
        verbose : bool
            Se True mostra l'output del solver.

        Restituisce
        -----------
        status : str
            Stato della soluzione: 'Optimal', 'Feasible', 'Infeasible', 'Undefined'.
        """
        prob, x = self.build_model()

        if solver is None:
            solver = pulp.PULP_CBC_CMD(
                timeLimit=time_limit,
                msg=1 if verbose else 0,
            )

        prob.solve(solver)

        self._status = pulp.LpStatus[prob.status]

        if prob.status in (1, -2):  # Optimal o Feasible (time limit)
            self._start_times = {}
            for i in self._activities:
                for t, var in x[i].items():
                    if pulp.value(var) is not None and pulp.value(var) > 0.5:
                        self._start_times[i] = t
                        break
            last = self._n - 1
            self._makespan = self._start_times.get(last)

        return self._status

    def get_schedule(self) -> list[dict]:
        """
        Restituisce la schedulazione come lista di dizionari, uno per attività.
        Richiede che solve() sia stato chiamato con successo.
        """
        if self._start_times is None:
            raise RuntimeError("Il modello non è ancora stato risolto. Chiamare solve() prima.")

        schedule = []
        for i in self._activities:
            s = self._start_times.get(i)
            schedule.append({
                "activity": i,
                "start": s,
                "end": s + self._durations[i] if s is not None else None,
                "duration": self._durations[i],
            })
        return sorted(schedule, key=lambda r: r["start"] or 0)
    
def has_cycle(n, precedences):
        """
        Metodo per controllare che il grafo delle precedenze non abbia un ciclo.
        """
        from collections import defaultdict, deque

        graph = defaultdict(list)
        indegree = [0]*n

        for i, j in precedences:
            graph[i].append(j)
            indegree[j] += 1

        queue = deque([i for i in range(n) if indegree[i] == 0])
        visited = 0

        while queue:
            node = queue.popleft()
            visited += 1
            for nei in graph[node]:
                indegree[nei] -= 1
                if indegree[nei] == 0:
                    queue.append(nei)

        return visited != n

def test_modulo():
    import time
    """
    Metodo per testare il modulo quando eseguito. I dati di input sono inventati.
    """
    num_attività = 10
    durate = [0, 4, 5, 7, 3, 14, 1, 5, 7, 0]
    precedenze = [(1, 2), (5, 6)]
    risorse = [8, 6]
    consumo = [[0, 0],
               [4, 3],
               [5, 0],
               [0, 6],
               [8, 6],
               [5, 4],
               [1, 4],
               [0, 6],
               [8, 0],
               [0, 0],
               ]
    scadenza = 40

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
    print(f"-"*60)
    print(f"Il solver ha impiegato {end_time-start_time:.6f} secondi")
    print(f"-"*60)
    print(schedula)
    print(f"="*60)

if __name__ == "__main__":
    test_modulo()



    