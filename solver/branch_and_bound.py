from solver.dataclasses.base_data_b_and_b import BaseDataBAndB
from solver.dataclasses.best_config_b_and_b import BestConfigBAndB
from solver.dataclasses.soluzione_orchestrator import SoluzioneOrchestrator
from solver.dataclasses.best_solution_b_and_b import BestSolutionBAndB
from solver.preprocessing import _pre_processing_rcpsp_max
import networkx as nx
import math
import copy

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
        self._visited = set()

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
                durations_fixed = self._fix_to_min(self.base_data.durations)
                resources_fixed = self._fix_to_max(self.base_data.resources)
                release_dates_fixed = self._fix_to_min(self.base_data.release_dates)
                due_dates_fixed = self._fix_to_max(self.base_data.due_dates)
                self._best_ub = self._compute_ub(durations_fixed, resources_fixed, release_dates_fixed, due_dates_fixed)
                self._best_config = BestConfigBAndB(durations=durations_fixed, resources=resources_fixed, release_dates=release_dates_fixed, due_dates=due_dates_fixed)
                self._branch(self._best_config.model_dump())
                return None

    def _branch(self, config):

        # Controllo se la configurazione è già stata visitata
        key = (
            tuple(config["durations"]),
            tuple(config["resources"]),
            tuple(config["release_dates"]),
            tuple(config["due_dates"])
        )

        if key in self._visited:
            return
        
        self._visited.add(key)

        # ---------- LB ----------

        processed = _pre_processing_rcpsp_max(
            n=self.base_data.n,
            durations=config["durations"],
            precedences=self.base_data.precedences,
            resources=config["resources"],
            consumption=self.base_data.consumption,
            horizon=self.base_data.horizon,
            release_dates=config["release_dates"],
            due_dates=config["due_dates"]
        )

        LB = self._compute_lb(
            processed.n,
            processed.durations,
            processed.precedences,
            processed.consumption,
            processed.resources,
            processed.release_dates
        )

        # pruning
        if LB >= self._best_ub:
            return

        # ---------- UB ----------
        sol = self._compute_ub(
            config["durations"],
            config["resources"],
            config["release_dates"],
            config["due_dates"]
        )

        UB = sol.get("best").get("best").get("makespan", float("inf")) if isinstance(sol.get("best").get("best"), dict) else float("inf")

        if UB < self._best_ub:
            self._best_ub = UB
            self._best_config = copy.deepcopy(config)
            self._best_solution_orchestrator = sol

        # ---------- branching ----------
        var = self._select_branch_variable(config)

        if var is None:
            return  # tutto fissato

        field, i = var
        val = config[field][i]
        if not isinstance(val, tuple):
            return 
        low, high = val

        # LOW branch
        new_config = {k: v.copy() for k, v in config.items()}
        new_config[field][i] = low
        self._branch(new_config)

        # HIGH branch
        new_config = {k: v.copy() for k, v in config.items()}
        new_config[field][i] = high
        self._branch(new_config)
            
    def _select_branch_variable(self, config):
        best = None
        best_width = -1

        for field in ["durations", "resources", "release_dates", "due_dates"]:
            for i, val in enumerate(config[field]):
                if isinstance(val, tuple):
                    width = val[1] - val[0]
                    if width > best_width:
                        best_width = width
                        best = (field, i)

        return best

    def _fix_to_min(self, lista):
        return [min(d) if isinstance(d, tuple) else d for d in lista]

    def _fix_to_max(self, lista):
        return [max(r) if isinstance(r, tuple) else r for r in lista]

    def _compute_lb(self, n, durations, precedences, consumption, resources, release_dates):

        lb_cpm = self._compute_cpm_lb(
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

        return max(lb_cpm, lb_res)

    def _compute_cpm_lb(self, n, durations, precedences, release_dates):
        
        G = nx.DiGraph()

        activities = list(range(n))

        # Aggiunta nodi
        G.add_nodes_from(activities)

        # Aggiunta archi e precedenze
        for (i, j, min_lag, max_lag) in precedences:
            G.add_edge(i, j, weight=min_lag)

        # Aggiunta release dates
        for i in activities:
            if release_dates[i] is not None:
                G.add_edge(0, i, weight=release_dates[i])
        
        # Check del DAG (Directed Acyclic Graph)
        if not nx.is_directed_acyclic_graph(G):
            raise ValueError("Il grafo delle attività e delle precedenze contiene cicli, impossibile calcolare il CPM.")
        
        # Calcolo del percorso critico (longest path) usando ordinamento topologico
        topo_order = list(nx.topological_sort(G))
        dist = {i: float("-inf") for i in activities}
        dist[0] = 0

        for u in topo_order:
            for v in G.successors(u):
                w = G[u][v]["weight"]
                dist[v] = max(dist[v], dist[u] + w)

        # Makespan = max(start_i + durata_i)
        makespan_lb = max(dist[i] + durations[i] for i in activities)

        return makespan_lb

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

        return self.orch.choose_model(n=self.base_data.n, durations=durations, precedences=self.base_data.precedences, resources=resources,
                                    consumption=self.base_data.consumption, horizon=self.base_data.horizon, release_dates=release_dates, 
                                    due_dates=due_dates, top_k=self.top_k, time_weight=self.time_weight, resource_weight=self.resource_weight, priority_weight=self.priority_weight, 
                                    tardiness_weight=self.tardiness_weight, limit_lookahead=self.limit_lookahead, instant_sol=True, priority_rule=self.priority_rule, rcpsp_max=True)

    
    @property
    def best_ub(self):
        return self._best_ub
    
    @property
    def best_config(self):
        return self._best_config
    
    def best_solution(self):
        if self._best_ub is None or self._best_config is None:
            return None
        return BestSolutionBAndB(config=BestConfigBAndB(**self._best_config), solution=SoluzioneOrchestrator(**self._best_solution_orchestrator))