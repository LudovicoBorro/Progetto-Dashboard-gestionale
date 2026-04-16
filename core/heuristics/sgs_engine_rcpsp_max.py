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
            allow_infeasible: bool = True
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
        self._allow_infeasible = allow_infeasible
        self._penalty_ser = 0
        self._penalty_par = 0

        self._schedule_serial: list[dict[int, int, int]] | None = None
        self._makespan_serial: int | None = None
        self._schedule_parallel: list[dict[int, int, int]] | None = None
        self._makespan_parallel: int | None = None

        if validate_input:
            validate_inputs(self)

    def serial(self, priority_list):
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
        
        Il metodo assegna una penalità nei casi in cui:
            - Un'attività è difficilmente schedulabile
            - L'attività viene schedulata sforando il LS
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
 
            if not valid:
                if self._allow_infeasible:
                    # fallback: uso comunque i candidati
                    valid = candidates

                    # penalità per violazione finestre
                    for (j, es, ls) in candidates:
                        if es > ls:
                            self._penalty_ser += (es - ls)
                else:
                    raise RuntimeError(
                        f"Finestre temporali impossibili per tutti i candidati: "
                        f"{[(j, int(es), int(ls)) for j,es,ls in candidates]}. "
                        f"I vincoli max_lag/due_date sono insoddisfacibili con questa priority list."
                    )

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
                while t <= limit or self._allow_infeasible:

                    # controllo risorse
                    feasible = True
                    overuse_for_this_t = 0
                    for tau in range(t, t + durata_j):
                        if tau > self._horizon:
                            feasible = False
                            break
                        for r in range(len(self._resources)):
                            overuse = consumption_profile[r][tau] + self._consumption[j][r] - self._resources[r]
                            if overuse > 0:
                                overuse_for_this_t += overuse
                                if not self._allow_infeasible:
                                    feasible = False
                                    break
                        if not feasible:
                            break

                    if feasible:
                        # penalità se sforo Latest Start
                        if t > ls_j:
                            self._penalty_ser += (t - ls_j)

                        self._penalty_ser += overuse_for_this_t

                        start_times[j] = t
                        finish_times[j] = t + durata_j

                        for tau in range(t, t + durata_j):
                            for r in range(len(self._resources)):
                                consumption_profile[r][tau] += self._consumption[j][r]

                        scheduled.add(j)
                        scheduled_flag = True
                        break

                    # accumula penalità overflow risorse
                    for tau in range(t, t + durata_j):
                        for r in range(len(self._resources)):
                            over = consumption_profile[r][tau] - self._resources[r]
                            if over > 0:
                                self._penalty_ser += over

                    t += 1

                if scheduled_flag:
                    break

            # --- Time jump se nessuno schedulato ---
            if not scheduled_flag:
                # Raccogli tutti i finish time delle attività già schedulate
                # che cadono dopo il minimo ES tra i candidati validi
                min_es = min(int(es) for (_, es, _) in valid)
                future_events = sorted(set(
                    ft for ft in finish_times.values() if ft > min_es
                ))
 
                if not future_events:
                    raise RuntimeError(
                        f"Stallo irrecuperabile: risorse sature e nessun evento futuro. "
                        f"Candidati validi: {[(j, int(es), int(ls)) for j,es,ls in valid]}"
                    )
 
                for next_t in future_events:
                    for (j, es_j, ls_j) in valid:
                        if j == 0:
                            continue
                        ls_j_int = int(ls_j) if ls_j != float("inf") else self._horizon
                        t = max(next_t, int(es_j))
                        durata_j = self._durations[j]
                        while t <= ls_j_int:
                            feasible = True
                            overuse_total = 0
                            for tau in range(t, t + durata_j):
                                if tau > self._horizon:
                                    feasible = False
                                    break
                                for r in range(len(self._resources)):
                                    over = consumption_profile[r][tau] + self._consumption[j][r] - self._resources[r]
                                    if over > 0:
                                        overuse_total += over
                                        if not self._allow_infeasible:
                                            feasible = False
                                            break
                                if not feasible:
                                    break

                            if feasible:
                                if t > ls_j:
                                    self._penalty_ser += (t - ls_j)

                                self._penalty_ser += overuse_total
                                start_times[j] = t
                                finish_times[j] = t + durata_j

                                for tau in range(t, t + durata_j):
                                    for r in range(len(self._resources)):
                                        consumption_profile[r][tau] += self._consumption[j][r]

                                scheduled.add(j)
                                scheduled_flag = True
                                break
                            
                            if overuse_total > 0:
                                self._penalty_ser += overuse_total
                            t += 1

                        if scheduled_flag:
                            break

                    if scheduled_flag:
                        break
 
                if not scheduled_flag:
                    if self._allow_infeasible:
                        # forza scheduling del più urgente
                        j, es_j, ls_j = min(valid, key=lambda x: x[2])

                        t = int(es_j)

                        start_times[j] = t
                        finish_times[j] = t + self._durations[j]

                        for tau in range(t, t + self._durations[j]):
                            for r in range(len(self._resources)):
                                consumption_profile[r][tau] += self._consumption[j][r]

                        scheduled.add(j)
                        self._penalty_ser += self._horizon * 2  # penalità forte
                        continue
                    else:
                        raise RuntimeError(
                            f"Stallo irrecuperabile: impossibile schedulare dopo time jump. "
                            f"Candidati validi: {[(j, int(es), int(ls)) for j,es,ls in valid]}"
                        )
                
        # Attività dummy finale
        start_times[last] = max(start_times[i] + self._durations[i] for i in start_times)
        finish_times[last] = start_times[last]

        schedule = []
        for a, t in start_times.items():
            schedule.append(
                {"activity": a, "start": t, "end": finish_times[a]}
            )

        return sorted(schedule, key=lambda x: x["start"])

    def parallel(self, priority_list):
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

        Il metodo assegna una penalità nei casi in cui:
            - Un'attività è difficilmente schedulabile
            - L'attività viene schedulata sforando il LS
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
                    if self._allow_infeasible:
                        self._penalty_par += (es_j - ls_j)
 
                # Solo i job la cui finestra include t sono candidati ora
                if t < es_j or t > ls_j:
                    if not self._allow_infeasible:
                        continue
 
                eligible_with_windows.append((j, es_j, ls_j))
 
            # 3. Ordina candidati: 1° priority_list, 2° LS crescente (urgenza)
            eligible_with_windows.sort(
                key=lambda x: (priority_index[x[0]], x[2])
            )
 
            # 4. Tenta scheduling dei candidati
            scheduled_this_step = False
 
            for (j, es_j, ls_j) in eligible_with_windows:
                # Controllo risorse
                feasible = True
                overuse_total = 0

                for r in range(len(self._resources)):
                    over = current_usage[r] + self._consumption[j][r] - self._resources[r]
                    if over > 0:
                        overuse_total += over
                        if not self._allow_infeasible:
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

                if overuse_total > 0:
                    self._penalty_par += (overuse_total * self._durations[j])

                # Penalty temporale se t > ls_j
                if t > ls_j:
                    self._penalty_par += (t - ls_j)
            
            # 5. Avanzamento del tempo
            if not ongoing and not scheduled_this_step:
                # Niente in esecuzione e niente schedulato: possibile deadlock
                if next_times:
                    next_t = min(next_times)
                    if next_t <= t:
                        if self._allow_infeasible and eligible_with_windows:
                            j = min(eligible_with_windows, key=lambda x: priority_index[x[0]])[0]

                            start_times[j] = t
                            finish_times[j] = t + self._durations[j]

                            for r in range(len(self._resources)):
                                current_usage[r] += self._consumption[j][r]

                            ongoing.add(j)
                            scheduled.add(j)

                            self._penalty_par += 500
                            continue
                        else:
                            raise RuntimeError(
                                f"Deadlock al tempo {t}: next_times={next_times}, "
                                f"scheduled={sorted(scheduled)}"
                            )
                    t = next_t
                else:
                    if self._allow_infeasible:
                        remaining = [j for j in priority_list if j not in scheduled and j != last]
                        if remaining:
                            j = remaining[0]

                            start_times[j] = t
                            finish_times[j] = t + self._durations[j]

                            ongoing.add(j)
                            scheduled.add(j)

                            self._penalty_par += 500
                            continue
                    else:
                        raise RuntimeError(
                            f"Deadlock irrecuperabile al tempo {t}: "
                            f"nessuna attività eleggibile e nessun job in esecuzione."
                        )
            else:
                # Avanza al prossimo termine di un'attività in corso,
                # oppure all'ES più vicino se la finestra non è ancora raggiunta
                candidates_t: list[int] = []
                if ongoing:
                    candidates_t.append(min(finish_times[j] for j in ongoing))
                if next_times:
                    future_next = [nt for nt in next_times if nt > t]
                    if future_next:
                        candidates_t.append(min(future_next))
 
                if candidates_t:
                    t = min(candidates_t)
                else:
                    # Non ci sono più eventi futuri: il loop terminerà al prossimo giro
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
    
    @property
    def penalty_ser(self):
        return self._penalty_ser
    
    @property
    def penalty_par(self):
        return self._penalty_par

def test_modulo():
    from core.heuristics.priority_rules import wrapper_rule
    from tests.instance_rcpsp_and_rcpsp_max import Instance
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
        print(sgs.serial(priority_list))
    except Exception as e:
        print(e)
    print("-"*60)
    print("Testing sgs_engine parallelo:")
    try:
        print(sgs.parallel(priority_list))
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
        print(sgs.serial(priority_list))
    except Exception as e:
        print(e)
    print("-"*60)
    print("Testing sgs_engine parallelo:")
    try:
        print(sgs.parallel(priority_list))
    except Exception as e:
        print(e)
    print("\n")

    priority_list = wrapper_rule("grd", n=n, durations=durations, precedences_rcpsp_max=precedences_rcpsp_max, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA GRD (GREATEST RESOURCES DEMAND)")
    print("="*60)
    print("Testing sgs_engine seriale:")
    try:
        print(sgs.serial(priority_list))
    except Exception as e:
        print(e)
    print("-"*60)
    print("Testing sgs_engine parallelo:")
    try:
        print(sgs.parallel(priority_list))
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
        print(sgs.serial(priority_list))
    except Exception as e:
        print(e)
    print("-"*60)
    print("Testing sgs_engine parallelo:")
    print(sgs.parallel(priority_list))
    print("="*60)
    print("\n")

    priority_list = wrapper_rule("lst_rcpsp_max", n=n, durations=durations, precedences_rcpsp_max=precedences_rcpsp_max, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA LST (LAST STARTING TIME)")
    print("="*60)
    print("Testing sgs_engine seriale:")
    try:
        print(sgs.serial(priority_list))
    except Exception as e:
        print(e)
    print("-"*60)
    print("Testing sgs_engine parallelo:")
    print(sgs.parallel(priority_list))
    print("="*60)
    print("\n")

    priority_list = wrapper_rule("mslk_rcpsp_max", n=n, durations=durations, precedences_rcpsp_max=precedences_rcpsp_max, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA MSLK (MINIMUM SLACK TIME)")
    print("="*60)
    print("Testing sgs_engine seriale:")
    try:
        print(sgs.serial(priority_list))
    except Exception as e:
        print(e)
    print("-"*60)
    print("Testing sgs_engine parallelo:")
    try:
        print(sgs.parallel(priority_list))
    except Exception as e:
        print(e)
    print("="*60)
    print("\n")

    N = 100

    print("="*60)
    print("\n")
    print("="*60)
    print("Esecuzione multitest seriale e parallelo per ciascuna regola.")
    print(f"Ogni funzione verra eseguita {N} volte per regola.")

    list_regole = ['spt', 'mts', 'grd', 'lft_rcpsp_max', 'lst_rcpsp_max', 'mslk_rcpsp_max']

    for regola in list_regole:
        print(f"\n TEST REGOLA {regola.upper()}")
        if regola == 'mts':
            priority_list = wrapper_rule(regola, n=n, durations=durations, precedences_rcpsp=precedences_rcpsp, resources=resources, consumption=consumption,
                                horizon=horizon)
        else:
            priority_list = wrapper_rule(regola, n=n, durations=durations, precedences_rcpsp_max=precedences_rcpsp_max, resources=resources, consumption=consumption,
                                horizon=horizon)
        print("-"*60)
        print("Test seriale:")
        makespans, best_sol = test_multistart_stats_serial(sgs, priority_list, N)
        print(f"Lista di tutti i makespans trovati: {makespans}")
        print("-"*60)

        print("-"*60)
        print("Test parallelo:")
        makespans, best_sol = test_multistart_stats_parallel(sgs, priority_list, N)
        print(f"Lista di tutti i makespans trovati: {makespans}")
        print("-"*60)

def test_multistart_stats_parallel(sgs, priority_list, n_runs=100):

    import random

    makespans = []
    solutions = {}
    penalties = {}
    failures = 0

    for _ in range(n_runs):

        pl = priority_list.copy()
        random.shuffle(pl)

        try:
            sol = sgs.parallel(pl)
            makespan = max(x["end"] for x in sol)
            makespans.append(makespan)
            solutions[makespan] = sol
            penalties[makespan] = sgs.penalty_par()
        except RuntimeError:
            failures += 1

    if makespans:
        print(f"\nRuns: {n_runs}")
        print(f"Success: {len(makespans)}")
        print(f"Failures: {failures}")
        print(f"Best: {min(makespans)}")
        print(f"Avg: {sum(makespans)/len(makespans):.2f}")
        print(f"Worst: {max(makespans)}")
    else:
        print("Nessuna soluzione trovata")

    return makespans, solutions.get(min(makespans)), penalties

def test_multistart_stats_serial(sgs, priority_list, n_runs=100):

    import random

    makespans = []
    solutions = {}
    penalties = {}
    failures = 0

    for _ in range(n_runs):

        pl = priority_list.copy()
        random.shuffle(pl)

        try:
            sol = sgs.serial(pl)
            makespan = max(x["end"] for x in sol)
            makespans.append(makespan)
            penalties[makespan] = sgs.penalty_ser()
        except RuntimeError:
            failures += 1

    if makespans:
        print(f"\nRuns: {n_runs}")
        print(f"Success: {len(makespans)}")
        print(f"Failures: {failures}")
        print(f"Best: {min(makespans)}")
        print(f"Avg: {sum(makespans)/len(makespans):.2f}")
        print(f"Worst: {max(makespans)}")
    else:
        print("Nessuna soluzione trovata")

    return makespans, solutions.get(min(makespans)), penalties

if __name__ == "__main__":
    test_modulo()