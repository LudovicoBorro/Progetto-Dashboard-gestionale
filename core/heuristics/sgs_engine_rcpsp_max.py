"""
sgs_engine_rcpsp_max.py
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
import numpy as np

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
            validate_input: bool = True,
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
        
        # Inizializzazione
        preds_map = {j: [] for j in range(self._n)}
        for (i, j, min_lag, max_lag) in self._precedences:
            preds_map[j].append((i, min_lag, max_lag))

        start_times = {}
        finish_times = {}
        scheduled = set()

        # Orizzonte temporale massimo
        horizon = self._horizon

        consumption_profile = np.zeros((len(self._resources), horizon + 1), dtype=int)

        while len(scheduled) < self._n:

            # Filtro attività valide
            eligible = [
                j for j in priority_list
                if j not in scheduled
                and j != self._n - 1
                and all(i in scheduled for (i, _, _) in preds_map[j])
            ]

            if not eligible:
                raise RuntimeError("Ciclo o vincoli impossibili")
            
            # Scelgo l'attività prioritaria in base alla priority list
            eligible_set = set(eligible)

            for j in priority_list:
                if j in eligible_set:
                    break

            # Inizializzo il nodo iniziale
            if j == 0:
                start_times[j] = 0
                finish_times[j] = 0
                scheduled.add(j)
                continue
            
            # Calcolo l'earliest start con il time-lag
            es_j = 0
            for (i, min_lag, _) in preds_map[j]:
                es_j = max(es_j, start_times[i] + min_lag)

            # Considero la release date
            if self._release_dates and self._release_dates[j] is not None:
                es_j = max(es_j, self._release_dates[j])

            # Ricerco il tempo t >= es_j per cui l'attività sia schedulabile in base ai vincoli di risorse, capacità e max_lag
            t = es_j
            durata_j = self._durations[j]

            while True:
                
                # Controllo della due_date
                if self._due_dates and self._due_dates[j] is not None:
                    if t + durata_j > self._due_dates[j]:
                        raise RuntimeError(f"Infeasible: attività {j} non schedulabile a causa della due date")
                    
                # Controllo del max_lag
                valid = True
                for (i, _, max_lag) in preds_map[j]:
                    if max_lag is not None:
                        if t > start_times[i] + max_lag:
                            valid = False
                            break

                if not valid:
                    raise RuntimeError(f"Infeasible: attività {j} non schedulabile per violazione max_lag")

                # Controllo del consumo risorse
                feasible = True

                for tau in range(t, t + durata_j):
                    for r in range(len(self._resources)):
                        if consumption_profile[r][tau] + self._consumption[j][r] > self._resources[r]:
                            feasible = False
                            break
                    if not feasible:
                        break
                
                if feasible:
                    start_times[j] = t
                    finish_times[j] = t + durata_j

                    for tau in range(t, t + durata_j):
                        for r in range(len(self._resources)):
                            consumption_profile[r][tau] += self._consumption[j][r]
                    
                    scheduled.add(j)
                    break

                t += 1
        
        last = self._n - 1
        start_times[last] = max(start_times[i] + self._durations[i] for i in start_times)
        finish_times[last] = start_times[last]

        schedule = []
        for a, t in start_times.items():
            schedule.append(
                {"activity": a, "start": t, "end": finish_times[a]}
            )

        return sorted(schedule, key=lambda x: x["start"])

    def parallel(self, priority_list):

        # Inizializzazione
        preds_map = {j: [] for j in range(self._n)}
        for (i, j, min_lag, max_lag) in self._precedences:
            preds_map[j].append((i, min_lag, max_lag))

        start_times = {}
        finish_times = {}
        scheduled = set()
        ongoing = set()

        current_usage = np.zeros(len(self._resources), dtype=int)

        t = 0
        last = self._n - 1

        start_times[0] = 0
        finish_times[0] = 0
        scheduled.add(0)

        while len(scheduled) < self._n - 1:

            # Rimuovo le attività terminate
            finished = [j for j in ongoing if finish_times[j] == t]

            for j in finished:
                for r in range(len(self._resources)):
                    current_usage[r] -= self._consumption[j][r]
                ongoing.remove(j)

            # Cerco attività eleggibili
            eligible = [
                j for j in priority_list
                if j not in scheduled
                and j not in ongoing
                and j != last
                and all(i in start_times and start_times[i] + min_lag <= t
                        for (i, min_lag, _) in preds_map[j]
                )
            ]

            # Ordino le attività eleggibili per priorità
            eligible_set = set(eligible)
            eligible_sorted = [j for j in priority_list if j in eligible_set]

            next_times = []

            # Tento la schedulazione
            for j in eligible_sorted:

                # Calcolo le finestre temporali per ogni attività j
                ES_j = 0
                LS_j = float("inf")

                for (i, min_lag, max_lag) in preds_map[j]:
                    ES_j = max(ES_j, start_times[i] + min_lag)
                    if max_lag is not None:
                        LS_j = min(LS_j, start_times[i] + max_lag)

                # Controllo della due_date
                if self._due_dates and self._due_dates[j] is not None:
                    LS_j = min(LS_j, self._due_dates[j] - self._durations[j])

                # Controllo della release date
                if self._release_dates and self._release_dates[j] is not None:
                    ES_j = max(ES_j, self._release_dates[j])

                next_times.append(ES_j)
                
                # Controllo fattibilità
                if ES_j > LS_j:
                    raise RuntimeError(f"Infeasible time window per attività {j}")
                
                if t < ES_j or t > LS_j:
                    continue
                
                # Controllo usage
                feasible = True
                for r in range(len(self._resources)):
                    if current_usage[r] + self._consumption[j][r] > self._resources[r]:
                        feasible = False
                        break

                if feasible:
                    start_times[j] = t
                    finish_times[j] = t + self._durations[j]

                    for r in range(len(self._resources)):
                        current_usage[r] += self._consumption[j][r]

                    scheduled.add(j)
                    ongoing.add(j)

            # Vado avanti con il tempo
            if ongoing:
                t = min(finish_times[j] for j in ongoing) # scorro fino alla prossima t dove finisce un'attività
            else:
                if next_times:
                    t = max(t + 1, min(next_times))
                else:
                    t += 1

        # Ultimo nodo
        start_times[last] = max(finish_times.values())
        finish_times[last] = start_times[last]

        schedule = []
        for a, t in start_times.items():
            schedule.append(
                {"activity": a, "start": t, "end": finish_times[a]}
            )

        return sorted(schedule, key=lambda x: x["start"])

