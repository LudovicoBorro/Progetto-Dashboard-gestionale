from solver.dataclasses.base_data_b_and_b import BaseDataBAndB
from solver.dataclasses.best_config_b_and_b import BestConfigBAndB
from solver.dataclasses.soluzione_orchestrator import SoluzioneOrchestrator
from solver.dataclasses.best_solution_b_and_b import BestSolutionBAndB
from solver.preprocessing import _pre_processing_rcpsp_max
from time import time
import networkx as nx
import math
import copy
import heapq

class BranchAndBoundSolver:
    def __init__(self, orch, **kwargs):
        self.orch = orch
        self.base_data = BaseDataBAndB(**kwargs)
        self._best_ub = None
        self._best_config = None
        self._best_solution_orchestrator = None
        self.top_k = kwargs.get("top_k", 5)
        self.time_weight = kwargs.get("time_weight", 1)
        self.resource_weight = kwargs.get("resource_weight", 1)
        self.priority_weight = kwargs.get("priority_weight", 1)
        self.tardiness_weight = kwargs.get("tardiness_weight", 1)
        self.limit_lookahead = kwargs.get("limit_lookahead", 5)
        self.priority_rule = kwargs.get("priority_rule", "spt")
        self.max_nodes = kwargs.get("max_nodes", 5000)
        self.max_time = kwargs.get("max_time", 600)  # 10 minuti di default
        self.log_interval = kwargs.get("log_interval", 5) # secondi
        self._visited = set()
        self._n_chiamate = 0
        self._variables = []

    def esplora_soluzioni(self, instant_sol, rcpsp_max):
        # Questa funzione deve preuccuparsi di analizzare per prima cosa i dati in input,
        # se il problema è rcpsp classico allora ho già la soluzione, perchè fisso le durations a min
        # e le resources a max, e richiamo la funzione choose_model con istanze di RCPSP senza intervalli 
        # e faccio scegliere a lui il modello da lanciare.
        # Se invece è rcpsp_max, allora devo come prima cosa capire quali valori in input hanno intervalli,
        # perchè se ci sono solo le durate allora le fisso a min e richiamo choose_model, se invece ci sono durate 
        # e risorse fisso durate a min e risorse a max e richiamo choose_model, se invece ci sono durate, risorse e 
        # date di rilascio o scadenza allora faccio una ricerca più ampia. Nella ricerca più ampia devo fare inizializzazione
        # calcolando un LB iniziale e un UB iniziale. LB è calcolato fissando durate a min, risorse a max, release date a min e due date a max, 
        # e scegliendo LB = max (CPM, resource_bound). L'UB viene calcolato cercando una vera soluzione con gli stessi dati fissati come per LB.
        # Attenzione che una volta fissati i dati per LB e UB, devo lanciare il pre_processing prima di cercare le soluzioni. A questo punto il best UB = UB iniziale.
        # Successivamente, deve iniziare il ciclo di esplorazione, magari attraverso un algoritmo di ricorsione, dove in ogni nodo viene fissato un solo dato di un solo job,
        # i restanti dati vengono fissati come all'inizio. Eseguo preprocessing dei dati fissati, calcolo nuovo LB = max(CPM, resource_bound), se 
        # LB >= best UB allora scarto il nodo, altrimenti cerco un UB se LB è promettente altrimenti continuo. UB viene calcolato con con diverse config:
        # 1) con stessi valori usati per LB del nodo, 2) valore random dentro l'intervallo del job fissato. Per ogni modalità lancio sgs multistart un pò di volte
        # con tutte le priority rules e prendo la soluzione migliore. Se UB < best UB allora aggiorno best UB. Continuo fino a quando non esploro tutti i nodi o
        # o raggiungo un limite di tempo oppure fino a quando ho tagliato tutti i rami e non mi sono rimasti valori da fissare per tutti i job.
        # Alla fine ritorno best UB come soluzione migliore trovata, insieme alla configurazione di dati che ha portato a quella soluzione.

        if not rcpsp_max:
            durations_fixed = self._fix_to_min(self.base_data.durations)
            resources_fixed = self._fix_to_max(self.base_data.resources)
            result = self.orch.choose_model(n=self.base_data.n, durations=durations_fixed, precedences=self.base_data.precedences, resources=resources_fixed,
                                    consumption=self.base_data.consumption, horizon=self.base_data.horizon, top_k=self.top_k, instant_sol=instant_sol, priority_rule=self.priority_rule, rcpsp_max=False)
            return BestSolutionBAndB(BestConfigBAndB(durations_fixed, resources_fixed, None, None), BestSolutionBAndB(**result)) 
        else:
            only_durations = any(isinstance(d, tuple) for d in self.base_data.durations) and not any(isinstance(r, tuple) for r in self.base_data.resources) and not any(isinstance(rd, tuple) for rd in self.base_data.release_dates) and not any(isinstance(dd, tuple) for dd in self.base_data.due_dates)
            only_durations_resources = any(isinstance(d, tuple) for d in self.base_data.durations) and any(isinstance(r, tuple) for r in self.base_data.resources) and not any(isinstance(rd, tuple) for rd in self.base_data.release_dates) and not any(isinstance(dd, tuple) for dd in self.base_data.due_dates)
            if only_durations or only_durations_resources:
                durations_fixed = self._fix_to_min(self.base_data.durations)
                resources_fixed = self._fix_to_max(self.base_data.resources)
                result = self.orch.choose_model(n=self.base_data.n, durations=durations_fixed, precedences=self.base_data.precedences, resources=resources_fixed,
                                        consumption=self.base_data.consumption, horizon=self.base_data.horizon, top_k=self.top_k, time_weight=self.time_weight, 
                                        resource_weight=self.resource_weight, priority_weight=self.priority_weight, tardiness_weight=self.tardiness_weight, 
                                        limit_lookahead=self.limit_lookahead, instant_sol=instant_sol, priority_rule=self.priority_rule, rcpsp_max=True)
                return BestSolutionBAndB(BestConfigBAndB(durations_fixed, resources_fixed, self.base_data.release_dates, self.base_data.due_dates), BestSolutionBAndB(**result))
            else:
                # Inizializzo le durate a min, le risorse a max, le release date a min e le due date a max, e calcolo LB iniziale e UB iniziale
                self._n_chiamate = 0
                durations_fixed = self._fix_to_min(self.base_data.durations)
                resources_fixed = self._fix_to_max(self.base_data.resources)
                release_dates_fixed = self._fix_to_min(self.base_data.release_dates)
                due_dates_fixed = self._fix_to_max(self.base_data.due_dates)
                
                self._best_ub = float("inf")
                first_ub_result = self._compute_ub(durations_fixed, resources_fixed, release_dates_fixed, due_dates_fixed)
                best_inner = first_ub_result.get("best", {}).get("best", {})
                if isinstance(best_inner, dict):
                    self._best_ub = best_inner.get("score", float("inf"))
                    self._best_solution_orchestrator = first_ub_result
                    self._best_config = BestConfigBAndB(durations=durations_fixed, resources=resources_fixed, release_dates=release_dates_fixed, due_dates=due_dates_fixed)
                
                print(f"[INIT] Best UB iniziale: {self._best_ub}")

                # --- BEST-FIRST SEARCH ---
                queue = []
                
                initial_config = {
                    "durations": list(self.base_data.durations),
                    "resources": list(self.base_data.resources),
                    "release_dates": list(self.base_data.release_dates),
                    "due_dates": list(self.base_data.due_dates)
                }
                
                # Calcolo LB iniziale per la coda
                fixed_init = self._fix_config_for_ub(initial_config)
                try:
                    proc_init = _pre_processing_rcpsp_max(
                        n=self.base_data.n, durations=fixed_init["durations"], precedences=self.base_data.precedences,
                        resources=fixed_init["resources"], consumption=self.base_data.consumption, horizon=self.base_data.horizon,
                        release_dates=fixed_init["release_dates"], due_dates=fixed_init["due_dates"]
                    )
                    lb_init, crit_init = self._compute_lb(
                        proc_init.n, proc_init.durations, proc_init.precedences, 
                        proc_init.consumption, proc_init.resources, proc_init.release_dates
                    )
                    # Inserisco il nodo radice
                    heapq.heappush(queue, (lb_init, 0, initial_config, crit_init)) # 0 è un counter
                except:
                    print("[ERROR] Impossibile inizializzare il B&B (preprocessing fallito)")
                    return None
                
                node_counter = 0
                start_time = time()
                last_log_time = start_time
                
                while queue:
                    lb, _, config, critical_activities = heapq.heappop(queue)
                    self._n_chiamate += 1
                    
                    # Controllo limiti
                    curr_time = time()
                    elapsed = curr_time - start_time
                    if self._n_chiamate > self.max_nodes or elapsed > self.max_time:
                        reason = "Limite nodi" if self._n_chiamate > self.max_nodes else "Limite tempo"
                        print(f"[WARNING] B&B interrotto: {reason}. Miglior UB trovato: {self._best_ub}")
                        break

                    if lb >= self._best_ub:
                        continue 
                    
                    # --- BRANCHING ---
                    var = self._select_best_variable(config, critical_activities)
                    if var is None:
                        # Abbiamo raggiunto una foglia (tutti i valori sono fissati o non ci sono più intervalli)
                        fixed = self._fix_config_for_ub(config)
                        sol = self._compute_ub(fixed["durations"], fixed["resources"], fixed["release_dates"], fixed["due_dates"])
                        best_inner = sol.get("best", {}).get("best", {})
                        if isinstance(best_inner, dict):
                            ub_score = best_inner.get("score", float("inf"))
                            if ub_score < self._best_ub:
                                self._best_ub = ub_score
                                self._best_config = copy.deepcopy(fixed)
                                self._best_solution_orchestrator = sol
                                print(f"[DEBUG #{self._n_chiamate}] Nuova Foglia Migliore: {self._best_ub}")
                        continue
                    
                    field, i = var
                    val = config[field][i]
                    low, high = val
                    
                    # Branching strategy: create two children and evaluate their LB/critical activities
                    for choice in [low, high]:
                        conf_new = copy.deepcopy(config)
                        conf_new[field][i] = choice
                        
                        # Evaluate child
                        fixed_new = self._fix_config_for_ub(conf_new)
                        try:
                            proc_new = _pre_processing_rcpsp_max(
                                n=self.base_data.n, durations=fixed_new["durations"], precedences=self.base_data.precedences,
                                resources=fixed_new["resources"], consumption=self.base_data.consumption, horizon=self.base_data.horizon,
                                release_dates=fixed_new["release_dates"], due_dates=fixed_new["due_dates"]
                            )
                            lb_new, crit_new = self._compute_lb(
                                proc_new.n, proc_new.durations, proc_new.precedences, 
                                proc_new.consumption, proc_new.resources, proc_new.release_dates
                            )
                            
                            if lb_new < self._best_ub:
                                node_counter += 1
                                # Heuristic update: if node is very promising, try to find a full solution (UB)
                                if node_counter % 250 == 0: # Ogni tanto prova a cercare una soluzione anche non in foglia
                                    sol_heur = self._compute_ub(fixed_new["durations"], fixed_new["resources"], fixed_new["release_dates"], fixed_new["due_dates"])
                                    inner_heur = sol_heur.get("best", {}).get("best", {})
                                    if isinstance(inner_heur, dict) and inner_heur.get("score", float("inf")) < self._best_ub:
                                        self._best_ub = inner_heur["score"]
                                        self._best_config = copy.deepcopy(fixed_new)
                                        self._best_solution_orchestrator = sol_heur
                                        print(f"[DEBUG #{self._n_chiamate}] Nuovo UB euristico trovato: {self._best_ub}")

                                heapq.heappush(queue, (lb_new, node_counter, conf_new, crit_new))
                        except:
                            continue
                    
                    # Feedback periodico
                    if curr_time - last_log_time > self.log_interval:
                        nodes_per_sec = self._n_chiamate / elapsed if elapsed > 0 else 0
                        print(f"[PROGRESS] Nodi: {self._n_chiamate} | Coda: {len(queue)} | Best UB: {self._best_ub:.2f} | LB: {lb:.2f} | Speed: {nodes_per_sec:.1f} n/s")
                        last_log_time = curr_time
                
                end_time = time()
                print(f"B&B Terminato. Nodi esplorati: {self._n_chiamate} | Tempo: {(end_time - start_time) / 60:.2f} min")
                return self.best_solution()

    def _select_best_variable(self, config, critical_activities):
        """Seleziona la variabile con intervallo dando priorità a quelle critiche e con intervallo più grande."""
        best_var = None
        max_diff = -1
        
        # Priorità 1: Attività critiche
        for field in ["durations", "resources", "release_dates", "due_dates"]:
            for i, val in enumerate(config[field]):
                if isinstance(val, tuple) and i in critical_activities:
                    diff = val[1] - val[0]
                    if diff > max_diff:
                        max_diff = diff
                        best_var = (field, i)
        
        if best_var:
            return best_var

        # Priorità 2: Qualsiasi altra attività con intervallo
        for field in ["durations", "resources", "release_dates", "due_dates"]:
            for i, val in enumerate(config[field]):
                if isinstance(val, tuple):
                    diff = val[1] - val[0]
                    if diff > max_diff:
                        max_diff = diff
                        best_var = (field, i)
        
        return best_var

    def _estimate_lb_for_config(self, config):
        fixed = self._fix_config_for_ub(config)
        try:
            processed = _pre_processing_rcpsp_max(
                n=self.base_data.n, durations=fixed["durations"], precedences=self.base_data.precedences,
                resources=fixed["resources"], consumption=self.base_data.consumption, horizon=self.base_data.horizon,
                release_dates=fixed["release_dates"], due_dates=fixed["due_dates"]
            )
            lb, _ = self._compute_lb(
                processed.n, processed.durations, processed.precedences, 
                processed.consumption, processed.resources, processed.release_dates
            )
            return lb
        except:
            return float("inf")
    
    def _fix_config_for_ub(self, config):
        """Fisso la config per il calcolo dell'UB. Considero lo stesso scenario iniziale, quindi quello più ottimistico."""
        return{
            "durations": self._fix_to_min(config["durations"]),
            "resources": self._fix_to_max(config["resources"]),
            "release_dates": self._fix_to_min(config["release_dates"]),
            "due_dates": self._fix_to_max(config["due_dates"]),
        }

    def _fix_to_min(self, lista):
        return [min(d) if isinstance(d, tuple) else d for d in lista]

    def _fix_to_max(self, lista):
        return [max(r) if isinstance(r, tuple) else r for r in lista]

    def _compute_lb(self, n, durations, precedences, consumption, resources, release_dates):

        lb_cpm, critical_activities = self._compute_cpm_lb(
            n=n,
            durations=durations,
            precedences=precedences,
            release_dates=release_dates
        )

        lb_res = self._compute_resource_bound_lb(
            durations=durations,
            consumption=consumption,
            resources=resources
        )

        final_lb = max(lb_cpm, lb_res)
        return final_lb, critical_activities

    def _compute_cpm_lb(self, n, durations, precedences, release_dates):
        
        G = nx.DiGraph()
        activities = list(range(n))
        G.add_nodes_from(activities)

        for (i, j, min_lag, _) in precedences:
            G.add_edge(i, j, weight=min_lag)

        for i in activities:
            if i != 0 and release_dates[i] is not None:
                rd = release_dates[i]
                if G.has_edge(0, i):
                    G[0][i]["weight"] = max(G[0][i]["weight"], rd)
                else:
                    G.add_edge(0, i, weight=rd)
        
        if not nx.is_directed_acyclic_graph(G):
            raise ValueError("Il grafo delle attività e delle precedenze contiene cicli, impossibile calcolare il CPM.")
        
        topo_order = list(nx.topological_sort(G))
        dist = {i: float("-inf") for i in activities}
        dist[0] = 0

        for u in topo_order:
            for v in G.successors(u):
                w = G[u][v]["weight"]
                if dist[u] + w > dist[v]:
                    dist[v] = dist[u] + w

        finish_times = {i: dist[i] + durations[i] for i in activities}
        makespan_lb = max(finish_times.values())

        # Identificazione attività critiche (quelle che determinano il makespan)
        critical_activities = set()
        for i in activities:
            if finish_times[i] == makespan_lb:
                # Questa attività finisce al tempo del makespan, è potenzialmente critica
                critical_activities.add(i)
                # Risaliamo all'indietro per trovare tutti i predecessori critici
                stack = [i]
                while stack:
                    curr = stack.pop()
                    for pred in G.predecessors(curr):
                        if dist[curr] == dist[pred] + G[pred][curr]["weight"]:
                            if pred not in critical_activities:
                                critical_activities.add(pred)
                                stack.append(pred)

        return makespan_lb, critical_activities

    def _compute_resource_bound_lb(self, durations, consumption, resources):
        
        n = len(durations)
        num_resources = len(resources)

        lb_values = []

        for k in range(num_resources):

            total_work = sum(durations[i] * consumption[i][k] for i in range(n))

            if resources[k] < 0:
                raise ValueError(f"Capacità della risorsa {k} non può essere negativo.")
            if resources[k] == 0:
                raise ValueError(f"Capacità della risorsa {k} non può essere zero.")

            lb_k = total_work / resources[k]
            lb_values.append(lb_k)
        
        return math.ceil(max(lb_values))

    def _compute_ub(self, durations, resources, release_dates, due_dates):

        result = self.orch.choose_model(
            n=self.base_data.n,
            durations=durations,
            precedences=self.base_data.precedences,
            resources=resources,
            consumption=self.base_data.consumption,
            horizon=self.base_data.horizon,
            release_dates=release_dates,
            due_dates=due_dates,
            top_k=self.top_k,
            time_weight=self.time_weight,
            resource_weight=self.resource_weight,
            priority_weight=self.priority_weight,
            tardiness_weight=self.tardiness_weight,
            limit_lookahead=self.limit_lookahead,
            instant_sol=True,
            priority_rule=self.priority_rule,
            rcpsp_max=True,
        )

        return result

    def _validate_ub_solution(self, solution, durations, resources, release_dates, due_dates):
        schedule = self._extract_solution_schedule(solution)
        if not schedule or not isinstance(schedule, list):
            return False

        try:
            processed = _pre_processing_rcpsp_max(
                n=self.base_data.n,
                durations=durations,
                precedences=self.base_data.precedences,
                resources=resources,
                consumption=self.base_data.consumption,
                horizon=self.base_data.horizon,
                release_dates=release_dates,
                due_dates=due_dates,
            )
        except Exception:
            return False

        activity_times = {}
        for entry in schedule:
            if not isinstance(entry, dict):
                return False
            activity = entry.get("activity")
            start = entry.get("start")
            end = entry.get("end")
            if activity is None or start is None or end is None:
                return False
            if not isinstance(activity, int) or not isinstance(start, int) or not isinstance(end, int):
                return False
            if end < start:
                return False
            duration = entry.get("duration")
            if duration is not None and duration != end - start:
                return False
            if activity in activity_times:
                return False
            activity_times[activity] = (start, end)

        if len(activity_times) != processed.n:
            return False

        for i in range(processed.n):
            if i not in activity_times:
                return False

        for (i, j, min_lag, max_lag) in processed.precedences:
            start_i = activity_times[i][0]
            start_j = activity_times[j][0]
            if start_j < start_i + min_lag:
                return False
            if max_lag is not None and start_j > start_i + max_lag:
                return False

        for i, (start, end) in activity_times.items():
            if processed.release_dates[i] is not None and start < processed.release_dates[i]:
                return False
            if processed.due_dates[i] is not None and end > processed.due_dates[i]:
                return False

        return True

    def _extract_solution_schedule(self, solution):
        if not isinstance(solution, dict):
            return None

        best = solution.get("best")
        if best is None:
            return None

        if isinstance(best.get("best"), dict):
            inner = best["best"]
            return inner.get("soluzione") or inner.get("schedule")

        return best.get("soluzione") or best.get("schedule")

    @property
    def best_ub(self):
        return self._best_ub
    
    @property
    def best_config(self):
        return self._best_config
    
    def best_solution(self):
        if self._best_ub is None or self._best_config is None or self._best_solution_orchestrator is None:
            return None
        return BestSolutionBAndB(config=self._best_config, solution=SoluzioneOrchestrator(**self._best_solution_orchestrator))