"""
sgs_engine_rcpsp_max.py
------------------------
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
        self._penalty_ser = 0
        self._penalty_par = 0

        self._schedule_serial: list[dict[int, int, int]] | None = None
        self._makespan_serial: int | None = None
        self._schedule_parallel: list[dict[int, int, int]] | None = None
        self._makespan_parallel: int | None = None

        if validate_input:
            validate_inputs(self)

    def serial(self, priority_list, time_weight, resource_weight, priority_weight, tardiness_weight, limit_lookahead):
        """
        SGS seriale per RCPSP/Max.
 
        Ad ogni passo si sceglie un'attività dalla lista (la prima
        eleggibile secondo la priority_list) e si schedula al primo
        istante temporale fattibile all'interno della sua finestra [ES, LS].
 
        Recovery da stallo (risorse sature per tutti):
            Se nessun candidato valido è schedulabile nelle sue finestre,
            si esegue un time jump al prossimo finish event delle attività
            già schedulate, riprovando a posizionare ciascun candidato
            a partire da quell'istante. Questo è il classico meccanismo
            backtrack-free del SGS seriale.
        
        Nel caso in cui il metodo non effettua una schedulazione rispettando
        i vincoli di tempo e risorse, viene calcolata una funzione di costo
        e effettuata la schedulazione in base ad essa, cercando appunto di 
        minimizzarla. Di conseguenza, la soluzione in questo caso potrebbe
        non rispettare i vincoli di risorse, di tempo o la lista di priorità.
        L'unica cosa che può influenzare la funzione di costo sono i pesi
        assegnati ad ogni vincolo.
        """
        self._penalty_ser = 0
        # Aggiungo le dummy activities nella priority_list
        priority_list = [0] + list(priority_list) + [self._n-1]

        priority_index = {job: i for i, job in enumerate(priority_list)}
        
        # Inizializzazione
        preds_map = {j: [] for j in range(self._n)}
        for (i, j, min_lag, max_lag) in self._precedences:
            preds_map[j].append((i, min_lag, max_lag))

        start_times = {}
        finish_times = {}
        scheduled = set()
        last = self._n - 1

        # Orizzonte temporale massimo
        horizon = self._horizon

        consumption_profile = np.zeros((len(self._resources), horizon + 1), dtype=int)

        while len(scheduled) < self._n - 1:

            # Filtro attività valide
            eligible = [
                j for j in priority_list
                if j not in scheduled
                and j != self._n - 1
                and all(i in scheduled for (i, _, _) in preds_map[j])
            ]

            if not eligible:
                raise RuntimeError(
                    f"Impossibile trovare attività eleggibili con {len(scheduled)} "
                    f"attività schedulate su {self._n}. Possibile ciclo o vincoli "
                    f"insoddisfacibili."
                )

            candidates = []

            for j in eligible:

                if j == 0:
                    candidates.append((j, 0, float("inf")))
                    continue

                es_j = 0
                ls_j = float("inf")

                for (i, min_lag, max_lag) in preds_map[j]:
                    es_j = max(es_j, start_times[i] + min_lag)
                    if max_lag is not None:
                        ls_j = min(ls_j, start_times[i] + max_lag)

                # release date
                if self._release_dates and self._release_dates[j] is not None:
                    es_j = max(es_j, self._release_dates[j])

                # due date
                if self._due_dates and self._due_dates[j] is not None:
                    ls_j = min(ls_j, self._due_dates[j] - self._durations[j])

                candidates.append((j, es_j, ls_j))

            # ordinamento: prima priority list, poi urgenza (LS)
            candidates.sort(key=lambda x: (priority_index[x[0]], x[2]))

            # Filtra candidati con finestra valida (ES <= LS)
            valid = [(j, es, ls) for (j, es, ls) in candidates if es <= ls]
 
            # if not valid:
                # raise RuntimeError(
                    # f"Finestre temporali impossibili per tutti i candidati: "
                    # f"{[(j, int(es), int(ls)) for j,es,ls in candidates]}. "
                    # f"I vincoli max_lag/due_date sono insoddisfacibili con questa priority list."
                # )

            scheduled_flag = False 

            for (j, es_j, ls_j) in valid:

                # nodo iniziale
                if j == 0:
                    start_times[j] = 0
                    finish_times[j] = 0
                    scheduled.add(j)
                    scheduled_flag = True
                    break

                t = int(es_j)
                durata_j = self._durations[j]
                ls_j = int(ls_j) if ls_j != float("inf") else self._horizon
                
                limit = ls_j if ls_j != float("inf") else self._horizon

                # Cerca il primo t ∈ [es_j, ls_j] con risorse disponibili
                while t <= limit:

                    # controllo risorse
                    feasible = True
                    for tau in range(t, t + durata_j):
                        if tau > self._horizon:
                            feasible = False
                            break
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
                        scheduled_flag = True
                        break

                    t += 1

                if scheduled_flag:
                    break

            # --- Time jump se nessuno schedulato ---
            if not scheduled_flag:
                # Nel caso in cui nessuna attività venga schedulata, schedulo forzatamente
                # quella con il costo minore calcolato nella funzione _compute_cost()

                best_cost = float("inf")
                best_choice = None

                if len(candidates) == 0:
                    raise RuntimeError("Fallback impossibile: nessun candidato disponibile")

                for (j, es_j, ls_j) in candidates:
                    if es_j > ls_j:
                        start = max(t, ls_j)
                        end = start + limit_lookahead
                    else:
                        start = max(t, es_j)
                        end = start + limit_lookahead
                    for t_cand in range(start, end):
                        cost, _ = self._compute_cost(j, t_cand, es_j, ls_j, priority_index, consumption_profile, time_weight=time_weight, resource_weight=resource_weight, priority_weight=priority_weight, tardiness_weight=tardiness_weight)
                        if cost < best_cost:
                            best_cost = cost
                            best_choice = (j, t_cand)
                
                j_fb = best_choice[0]
                t = best_choice[1]
                start_times[j_fb] = t
                finish_times[j_fb] = t + self._durations[j_fb]

                for tau in range(t, t + self._durations[j_fb]):
                    for r in range(len(self._resources)):
                        consumption_profile[r][tau] += self._consumption[j_fb][r]

                scheduled.add(j_fb)
                self._penalty_ser += best_cost
                continue
                
        # Attività dummy finale
        start_times[last] = max(start_times[i] + self._durations[i] for i in start_times)
        finish_times[last] = start_times[last]

        schedule = []
        for a, t in start_times.items():
            schedule.append(
                {"activity": a, "start": t, "end": finish_times[a]}
            )

        return sorted(schedule, key=lambda x: x["start"])

    def parallel(self, priority_list, time_weight, resource_weight, priority_weight, tardiness_weight, limit_lookahead):
        """
        SGS parallelo per RCPSP/Max.
 
        Ad ogni istante t si schedula tutto ciò che è eleggibile,
        ha finestra [ES, LS] che include t ed è compatibile con le risorse.
        Il tempo avanza al prossimo evento rilevante (fine di un'attività
        in corso o ES futuro di un'attività eleggibile).
 
        Nota: il parallelo in RCPSP/Max produce makespans tipicamente
        peggiori del seriale perché impegna risorse "presto" impedendo
        schedulazioni più efficienti. Questo è un comportamento atteso
        e non un bug — il parallelo è utile per la sua velocità e
        robustezza, non per la qualità della soluzione.

        Nel caso in cui il metodo non effettua una schedulazione rispettando
        i vincoli di tempo e risorse, viene calcolata una funzione di costo
        e effettuata la schedulazione in base ad essa, cercando appunto di 
        minimizzarla. Di conseguenza, la soluzione in questo caso potrebbe
        non rispettare i vincoli di risorse, di tempo o la lista di priorità.
        L'unica cosa che può influenzare la funzione di costo sono i pesi
        assegnati ad ogni vincolo.
        """
        self._penalty_par = 0
        # Aggiungo le dummy activities nella priority_list
        priority_list = [0] + priority_list + [self._n-1]

        priority_index = {job: i for i, job in enumerate(priority_list)}

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

            # Rimuovo le attività terminate al tempo t
            finished_now = [j for j in list(ongoing) if finish_times[j] <= t]
            for j in finished_now:
                for r in range(len(self._resources)):
                    current_usage[r] -= self._consumption[j][r]
                ongoing.discard(j)

            # 2. Calcola finestre per tutti i job non ancora schedulati/ongoing
            #    (inclusi quelli con predecessori non ancora schedulati, per determinare
            #    next_times in modo da evitare deadlock)
            eligible_with_windows: list[tuple[int, int, float]] = []
            candidates_global = []
            next_times: list[int] = []
 
            for j in priority_list:
                if j in scheduled or j in ongoing or j == last:
                    continue
 
                # Controlla se tutti i predecessori sono schedulati
                all_preds_done = all(i in scheduled for (i, _, _) in preds_map[j])
 
                if not all_preds_done:
                    # Non ancora eleggibile, ma contribuisce a next_times se ha almeno
                    # un predecessore in ongoing (potenziale sblocco futuro)
                    continue
 
                # Calcola ES e LS
                es_j = 0
                ls_j = float("inf")
 
                for (i, min_lag, max_lag) in preds_map[j]:
                    es_j = max(es_j, start_times[i] + min_lag)
                    if max_lag is not None:
                        ls_j = min(ls_j, start_times[i] + max_lag)
 
                if self._release_dates and self._release_dates[j] is not None:
                    es_j = max(es_j, self._release_dates[j])
 
                if self._due_dates and self._due_dates[j] is not None:
                    ls_j = min(ls_j, self._due_dates[j] - self._durations[j])
 
                next_times.append(es_j)
 
                # Finestra infeasible: salto
                if es_j > ls_j:
                    candidates_global.append((j, es_j, ls_j))
                    continue
 
                eligible_with_windows.append((j, es_j, ls_j))
                candidates_global.append((j, es_j, ls_j))
 
            # 3. Ordina candidati: 1° priority_list, 2° LS crescente (urgenza)
            eligible_with_windows.sort(
                key=lambda x: (priority_index[x[0]], x[2])
            )
            candidates_global.sort(key=lambda x: (priority_index[x[0]], x[2]))
 
            # 4. Tenta scheduling dei candidati
            scheduled_this_step = False
 
            for (j, es_j, ls_j) in eligible_with_windows:
                # Controllo risorse
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
                    scheduled_this_step = True
                
            # 5. Fallback in caso di mancata schedulazione o avanzamento nel tempo
            if not scheduled_this_step:
                best_cost = float("inf")
                best_choice = None

                if len(candidates_global) == 0:
                    raise("Fallback impossibile: nessuna attività eleggibile disponibile")

                for (j, es_j, ls_j) in candidates_global:
                    if j in scheduled or j in ongoing:
                        continue

                    if es_j > ls_j:
                        start = max(t, ls_j)
                        end = start + limit_lookahead
                    else:
                        start = max(t, es_j)
                        end = start + limit_lookahead
                    for t_cand in range(start, end):
                        cost, _ = self._compute_cost(j, t_cand, es_j, ls_j, priority_index, current_usage, time_weight=time_weight, resource_weight=resource_weight, priority_weight=priority_weight, tardiness_weight=tardiness_weight)
                        if cost < best_cost:
                            best_cost = cost
                            best_choice = (j, t_cand)

                if best_choice is None:
                    if ongoing:
                        t = min(finish_times[jj] for jj in ongoing)
                    else:
                        t += 1
                    continue

                j_fb = best_choice[0]
                t_fb = best_choice[1]
                if t_fb > t:
                    t = t_fb

                start_times[j_fb] = t
                finish_times[j_fb] = t + self._durations[j_fb]
                for r in range(len(self._resources)):
                    current_usage[r] += self._consumption[j_fb][r]
                scheduled.add(j_fb)
                ongoing.add(j_fb)
                scheduled_this_step = True
                self._penalty_par += best_cost

            if scheduled_this_step:    
                # Avanza al prossimo termine di un'attività in corso,
                # oppure all'ES più vicino se la finestra non è ancora raggiunta
                candidates_t: list[int] = []
                if ongoing:
                    candidates_t.append(min(finish_times[jj] for jj in ongoing))
                if next_times:
                    future_next = [nt for nt in next_times if nt > t]
                    if future_next:
                        candidates_t.append(min(future_next))

                if candidates_t:
                    t = min(candidates_t)
                else:
                    # Non ci sono più eventi futuri: il loop terminerà al prossimo giro
                    t += 1
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
    
    def _compute_cost(self, j, t, es_j, ls_j, priority_index, usage_profile, time_weight, resource_weight, priority_weight, tardiness_weight):
        """
        Metodo per calcolare la funzione di costo. 
        Viene chiamato ogni volta che un'attività non
        può essere schedulata in un determinato periodo.

        Per influenzare il comportamento dei metodi serial()
        e parallel(), è necessario modificare i pesi assegnati
        ad ogni vincolo, in particolare:
            - time_weight -> peso associato alla violazione della
              finestra temporale (es_j, ls_j)
            - resource_weight -> peso associato all'overuse delle 
              risorse
            - priority_weight -> peso associato alla lista di priorità
              generata dalle regola scelta
            - tardiness_weight -> peso associato al ritardo del job in
              questione, rispetto alla data di scadenza, se esiste  

        Nota: i costi sono normalizzati, perciò i pesi che si possono assegnare
        rientrano in una scala da 0 -> 5, dove 0 significa nessuna priorità,
        5 massima priorità per quel fattore. 
        """
        cost = 0
        time_penalty = 0
        overuse_penalty = 0
        tardiness_penalty = 0

        durata = self._durations[j]

        # --- 1. Violazione finestra ---
        if es_j <= ls_j:
            if t < es_j:
                time_penalty = (es_j - t) * time_weight
            if t > ls_j:
                time_penalty = (t - ls_j) * time_weight
        else:
            time_penalty = (es_j - ls_j) * (2*time_weight)  # Assegno un peso molto più grande nel caso in cui es_j > ls_j, 
                                                            # perchè significa che il job è infeasible e non ha lo stesso peso di 
                                                            # spostare il job nella finestra feasible
        cost += time_penalty

        # --- 2. Overuse risorse ---
        overuse = 0
        for tau in range(t, t + durata):
            if tau > self._horizon:
                overuse += 1000
                continue

            for r in range(len(self._resources)):
                if usage_profile.ndim == 2:
                    over = usage_profile[r][tau] + self._consumption[j][r] - self._resources[r]
                    if over > 0:
                        overuse += over
                else:
                    over = usage_profile[r] + self._consumption[j][r] - self._resources[r]
                    if over > 0:
                        overuse += over

        overuse_penalty = (overuse /(durata * len(self._resources))) * resource_weight

        cost += overuse_penalty

        # --- 3. Priorità (soft) ---
        priority_penalty = priority_index[j] * priority_weight
        cost += priority_penalty

        # --- 4. Ritardo globale ---
        if self._due_dates and self._due_dates[j] is not None:
            finish = t + durata
            tardiness = max(0, finish - self._due_dates[j])
            tardiness_penalty = tardiness * tardiness_weight
            cost += tardiness_penalty

        penalties = {"time_penalty": time_penalty, "overuse_penalty": overuse_penalty, "priority_penalty": priority_penalty, "tardiness_penalty": tardiness_penalty}
        return cost, penalties
    
    @property
    def penalty_ser(self):
        return self._penalty_ser
    
    @property
    def penalty_par(self):
        return self._penalty_par

def test_modulo():
    from core.heuristics.priority_rules import wrapper_rule
    from tests.instance_rcpsp_and_rcpsp_max import Instance
    from core.heuristics.multistart_rcpsp_max import get_best_solution_overall
    import random

    # Input 
    n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, horizon, consumption, release_dates, due_dates = Instance.get_instance()
    
    sgs = SGSEngine(n, durations, precedences_rcpsp_max, resources, consumption, horizon, release_dates=release_dates, due_dates=due_dates, validate_input=True)

    priority_list = wrapper_rule("spt", n=n, durations=durations, precedences_rcpsp_max=precedences_rcpsp_max, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA SPT (SHORTEST PROCESS TIME)")
    print("="*60)
    print("Testing sgs_engine seriale:")
    try:
        print(sgs.serial(priority_list, time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5))
    except Exception as e:
        raise e
    print("-"*60)
    print("Testing sgs_engine parallelo:")
    try:
        print(sgs.parallel(priority_list, time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5))
    except Exception as e:
        print(e)
    print("="*60)
    print("\n")

    priority_list = wrapper_rule("mts", n=n, durations=durations, precedences_rcpsp=precedences_rcpsp, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA MTS (MOST TOTAL SUCCESSORS)")
    print("="*60)
    print("Testing sgs_engine seriale:")
    try:
        print(sgs.serial(priority_list, time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5))
    except Exception as e:
        print(e)
    print("-"*60)
    print("Testing sgs_engine parallelo:")
    try:
        print(sgs.parallel(priority_list, time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5))
    except Exception as e:
        print(e)
    print("\n")

    priority_list = wrapper_rule("grd", n=n, durations=durations, precedences_rcpsp_max=precedences_rcpsp_max, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA GRD (GREATEST RESOURCES DEMAND)")
    print("="*60)
    print("Testing sgs_engine seriale:")
    try:
        print(sgs.serial(priority_list, time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5))
    except Exception as e:
        print(e)
    print("-"*60)
    print("Testing sgs_engine parallelo:")
    try:
        print(sgs.parallel(priority_list, time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5))
    except Exception as e:
        print(e)
    print("="*60)
    print("\n")

    priority_list = wrapper_rule("lft_rcpsp_max", n=n, durations=durations, precedences_rcpsp_max=precedences_rcpsp_max, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA LFT (LAST FINISHING TIME)")
    print("="*60)
    print("Testing sgs_engine seriale:")
    try:
        print(sgs.serial(priority_list, time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5))
    except Exception as e:
        print(e)
    print("-"*60)
    print("Testing sgs_engine parallelo:")
    print(sgs.parallel(priority_list, time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5))
    print("="*60)
    print("\n")

    priority_list = wrapper_rule("lst_rcpsp_max", n=n, durations=durations, precedences_rcpsp_max=precedences_rcpsp_max, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA LST (LAST STARTING TIME)")
    print("="*60)
    print("Testing sgs_engine seriale:")
    try:
        print(sgs.serial(priority_list, time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5))
    except Exception as e:
        print(e)
    print("-"*60)
    print("Testing sgs_engine parallelo:")
    print(sgs.parallel(priority_list, time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5))
    print("="*60)
    print("\n")

    priority_list = wrapper_rule("mslk_rcpsp_max", n=n, durations=durations, precedences_rcpsp_max=precedences_rcpsp_max, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA MSLK (MINIMUM SLACK TIME)")
    print("="*60)
    print("Testing sgs_engine seriale:")
    try:
        print(sgs.serial(priority_list, time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5))
    except Exception as e:
        print(e)
    print("-"*60)
    print("Testing sgs_engine parallelo:")
    try:
        print(sgs.parallel(priority_list, time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5))
    except Exception as e:
        print(e)
    print("="*60)
    print("\n")

    N = 1000

    print("="*60)
    print("\n")
    print("="*60)
    print("Esecuzione multitest seriale e parallelo per ciascuna regola.")
    print(f"Ogni funzione verra eseguita {N} volte per regola.")

    risultati, best_solution_overall, specs = get_best_solution_overall(sgs, n, durations, precedences_rcpsp, precedences_rcpsp_max, resources, consumption, horizon, N)

    for k, r in risultati.items():
        print(f"\n TEST REGOLA {k.upper()}")

        print("-"*60)
        print(f"Runs: {r.get("runs")}")
        print(f"Success: {r.get("success")}")
        print(f"Failures: {r.get("failures")}")
        print(f"Best: {r.get("best")}")
        print(f"Average: {r.get("average")}")
        print(f"Worst: {r.get("worst")}")
        print(f"Lista di tutti i makespans trovati: {r.get("makespans")}")
        print("-"*60)

    print("-"*60)
    print("La migliore soluzione in assoluto, tra tutte le regole di priorità e tra il seriale e il parallelo è:")
    print(f"Regola: {best_solution_overall["regola"]}")
    print(f"Makespan: {best_solution_overall["makespan"]}")
    print(f"Soluzione: {best_solution_overall["soluzione"]}")
    print(f"Penalità: {best_solution_overall["penalità"]}")
    print(f"Score: {best_solution_overall["score"]}")
    print("-"*60)

if __name__ == "__main__":
    test_modulo()