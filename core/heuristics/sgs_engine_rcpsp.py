"""
sgs_engine_rcpsp.py
-------------
Implementazione del motore che schedula le attività in modo da rispettare i vincoli
di precedenza e di risorsa del problema RCPSP classico.

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

from utils.validators.validate_input_rcpsp import validate_inputs
import numpy as np

class SGSEngine:

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

        self._schedule_serial: list[dict[int, int, int]] | None = None
        self._makespan_serial: int | None = None
        self._schedule_parallel: list[dict[int, int, int]] | None = None
        self._makespan_parallel: int | None = None

        if validate_input:
            validate_inputs(self)

    def serial(self, priority_list):

        # Aggiungo le dummy activities nella priority_list
        priority_list = [0] + priority_list + [self._n-1]
        
        # Inizializzazione
        preds_map = {i: [] for i in range(self._n)}
        for i, j in self._precedences:
            preds_map[j].append(i)
        
        start_times = {}
        finish_times = {}
        scheduled = set()

        # Definisco orizzonte temporale massimo (nel peggiore dei casi: tutte in serie)
        horizon = min(sum(self._durations), self._horizon)

        consumption_profile = np.zeros((len(self._resources), horizon + 1), dtype=int)

        # Ciclo principale SGS
        while len(scheduled) < self._n - 1:

            # Filtro le attività valide nella priority list,
            # cioè quelle che rispettano le precedenze
            eligible = [
                j for j in priority_list
                if j not in scheduled
                and j != self._n - 1
                and all(p in scheduled for p in preds_map[j])   # In questo modo verifico che l'attività j non sia già stata schedulata e che 
                                                                # tutti i predecessori siano schedulati
            ]

            if not eligible:
                raise RuntimeError("Attenzione: precedenze non valide o ciclo nel grafo")
            
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

            # Calcolo l'earliest start
            es_j = 0
            if preds_map[j]:
                es_j = max(finish_times[p] for p in preds_map[j])

            # Ricerco il tempo t >= es_j per cui l'attività sia schedulabile in base ai vincoli di risorse e capacità
            t = es_j
            durata_j = self._durations[j]

            while True:

                if t + durata_j > horizon:
                    raise RuntimeError(f"Attività {j} non schedulabile entro l'orizzonte")

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
        
        # Imposto il nodo finale
        last = self._n - 1
        start_times[last] = max(finish_times.values())
        finish_times[last] = start_times[last]

        schedule = []
        for a, t in start_times.items():
            schedule.append(
                {"activity": a, "start": t, "end": finish_times[a]}
            )
        
        return sorted(schedule, key=lambda x: x["start"])
    
    def parallel(self, priority_list):

        # Aggiungo le dummy activities nella priority_list
        priority_list = [0] + priority_list + [self._n-1]
        
        # Inizializzazione
        preds_map = {i: [] for i in range(self._n)}
        for i, j in self._precedences:
            preds_map[j].append(i)
        
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
                and all(p in scheduled and p not in ongoing for p in preds_map[j])
            ]

            # Ordino le attività eleggibili per priorità
            eligible_set = set(eligible)
            eligible_sorted = [j for j in priority_list if j in eligible_set]

            # Tento la schedulazione
            for j in eligible_sorted:

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

def test_modulo():
    from core.heuristics.priority_rules import wrapper_rule
    from tests.instance_rcpsp_and_rcpsp_max import Instance
    from core.heuristics.multistart_rcpsp import get_best_solution_overall

    # Input 
    n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, horizon, consumption, release_dates, due_dates = Instance.get_instance()

    priority_list = wrapper_rule("spt", n, durations, precedences_rcpsp, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    sgs = SGSEngine(n, durations, precedences_rcpsp, resources, consumption, horizon, validate_input=True)

    ENGINE_SERIAL = "Testing sgs_engine seriale:"
    ENGINE_PARALLEL = "Testing sgs_engine parallelo:"
    
    print("REGOLA SPT (SHORTEST PROCESS TIME)")
    print("="*60)
    print(ENGINE_SERIAL)
    print(sgs.serial(priority_list))
    print("-"*60)
    print(ENGINE_PARALLEL)
    print(sgs.parallel(priority_list))
    print("="*60)
    print("\n")

    priority_list = wrapper_rule("mts", n, durations, precedences_rcpsp, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA MTS (MOST TOTAL SUCCESSORS)")
    print("="*60)
    print(ENGINE_SERIAL)
    print(sgs.serial(priority_list))
    print("-"*60)
    print(ENGINE_PARALLEL)
    print(sgs.parallel(priority_list))
    print("="*60)
    print("\n")

    priority_list = wrapper_rule("grd", n, durations, precedences_rcpsp, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA GRD (GREATEST RESOURCES DEMAND)")
    print("="*60)
    print(ENGINE_SERIAL)
    print(sgs.serial(priority_list))
    print("-"*60)
    print(ENGINE_PARALLEL)
    print(sgs.parallel(priority_list))
    print("="*60)
    print("\n")

    priority_list = wrapper_rule("lft_rcpsp", n, durations, precedences_rcpsp, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA LFT (LAST FINISHING TIME)")
    print("="*60)
    print(ENGINE_SERIAL)
    print(sgs.serial(priority_list))
    print("-"*60)
    print(ENGINE_PARALLEL)
    print(sgs.parallel(priority_list))
    print("="*60)
    print("\n")

    priority_list = wrapper_rule("lst_rcpsp", n, durations, precedences_rcpsp, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA LST (LAST STARTING TIME)")
    print("="*60)
    print(ENGINE_SERIAL)
    print(sgs.serial(priority_list))
    print("-"*60)
    print(ENGINE_PARALLEL)
    print(sgs.parallel(priority_list))
    print("="*60)
    print("\n")

    priority_list = wrapper_rule("mslk_rcpsp", n, durations, precedences_rcpsp, resources=resources, consumption=consumption,
                                horizon=horizon)
    
    print("REGOLA MSLK (MINIMUM SLACK TIME)")
    print("="*60)
    print(ENGINE_SERIAL)
    print(sgs.serial(priority_list))
    print("-"*60)
    print(ENGINE_PARALLEL)
    print(sgs.parallel(priority_list))
    print("="*60)
    print("\n")

    N = 100

    print("="*60)
    print("\n")
    print("="*60)
    print("Esecuzione multitest seriale e parallelo per ciascuna regola.")
    print(f"Ogni funzione verra eseguita {N} volte per regola.")

    risultati, best_solution_overall = get_best_solution_overall(sgs, n, durations, precedences_rcpsp, resources, consumption, horizon, N)

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
    print("-"*60)



if __name__ == "__main__":
    test_modulo()