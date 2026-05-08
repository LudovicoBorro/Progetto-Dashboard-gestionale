from time import perf_counter
from datetime import datetime
from solver.dataclasses.input_data import InputData
from solver.dataclasses.best_config_b_and_b import BestConfigBAndB
from solver.dataclasses.soluzione_orchestrator import SoluzioneOrchestrator
from solver.dataclasses.best_solution_b_and_b import BestSolutionBAndB
from solver.preprocessing import _pre_processing_rcpsp_max
from time import time
import networkx as nx
import math
import copy
import heapq
import logging

class BranchAndBoundSolver:
    def __init__(self, orch, input_data: InputData = None, **kwargs):
        self.orch = orch
        if input_data:
            self.base_data = input_data
        else:
            self.base_data = InputData(**kwargs)
        self._best_ub = None
        self._best_config = None
        self._best_solution_orchestrator = None
        
        # I parametri sono ora centralizzati in InputData
        self.top_k = self.base_data.top_k
        self.time_weight = self.base_data.time_weight
        self.resource_weight = self.base_data.resource_weight
        self.priority_weight = self.base_data.priority_weight
        self.tardiness_weight = self.base_data.tardiness_weight
        self.limit_lookahead = self.base_data.limit_lookahead
        self.priority_rule = self.base_data.priority_rule or "spt"
        self.max_nodes = self.base_data.max_nodes
        self.max_time = self.base_data.max_time
        self.log_interval = kwargs.get("log_interval") or 5 # secondi
        self._n_chiamate = 0

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
                self._open_log_file()
                # Inizializzo le durate a min, le risorse a max, le release date a min e le due date a max, e calcolo LB iniziale e UB iniziale
                self._n_chiamate = 0
                config = {"durations": list(self.base_data.durations), "resources": list(self.base_data.resources), "release_dates": list(self.base_data.release_dates), "due_dates": list(self.base_data.due_dates)}
                self._variabili_totali_aperte = self._count_open_vars(config)
                durations_fixed = self._fix_to_min(config["durations"])
                resources_fixed = self._fix_to_max(config["resources"])
                release_dates_fixed = self._fix_to_min(config["release_dates"])
                due_dates_fixed = self._fix_to_max(config["due_dates"])
                
                self._best_ub = float("inf")
                first_ub_result = self._compute_ub(durations_fixed, resources_fixed, release_dates_fixed, due_dates_fixed)
                best_inner = first_ub_result.get("best", {}).get("best", {})
                if isinstance(best_inner, dict):
                    self._best_ub = self._get_score_from_solution(best_inner)
                    self._best_solution_orchestrator = first_ub_result
                    self._best_config = BestConfigBAndB(durations=durations_fixed, resources=resources_fixed, release_dates=release_dates_fixed, due_dates=due_dates_fixed)
                
                logging.info(f"[INIT] Best UB iniziale: {self._best_ub}")

                # --- BEST-FIRST SEARCH ---
                queue = []
                
                initial_config = {
                    "durations": list(self.base_data.durations),
                    "resources": list(self.base_data.resources),
                    "release_dates": list(self.base_data.release_dates),
                    "due_dates": list(self.base_data.due_dates)
                }
                
                # Calcolo LB iniziale per la coda
                fixed_init = self._fix_config_for_lb(initial_config)
                fixed_init_mid = self._fix_config_for_lb_mid(initial_config)
                try:
                    start = perf_counter()
                    proc_init = _pre_processing_rcpsp_max(
                        n=self.base_data.n, durations=fixed_init["durations"], precedences=self.base_data.precedences,
                        resources=fixed_init["resources"], consumption=self.base_data.consumption, horizon=self.base_data.horizon,
                        release_dates=fixed_init["release_dates"], due_dates=fixed_init["due_dates"]
                    )
                    proc_init_mid = _pre_processing_rcpsp_max(
                        n=self.base_data.n, durations=fixed_init_mid["durations"], precedences=self.base_data.precedences,
                        resources=fixed_init_mid["resources"], consumption=self.base_data.consumption, horizon=self.base_data.horizon,
                        release_dates=fixed_init_mid["release_dates"], due_dates=fixed_init_mid["due_dates"]
                    )
                    logging.debug(f"Pre-processing completato in {perf_counter() - start:.2f} secondi")
                    start = perf_counter()
                    lb_init, crit_init = self._compute_lb(
                        proc_init.n, proc_init.durations, proc_init.precedences, 
                        proc_init.consumption, proc_init.resources, proc_init.release_dates
                    )
                    heuristic_init_lb, crit_init_mid = self._compute_lb(
                        proc_init_mid.n, proc_init_mid.durations, proc_init_mid.precedences, 
                        proc_init_mid.consumption, proc_init_mid.resources, proc_init_mid.release_dates
                    )
                    logging.debug(f"LB calcolati in {perf_counter() - start:.2f} secondi")
                    logging.debug(f"LB euristico e ottimistico iniziale calcolato: {heuristic_init_lb:.2f}, {lb_init:.2f}")
                    # Inserisco il nodo radice
                    heapq.heappush(queue, (heuristic_init_lb, lb_init, 0, initial_config, crit_init_mid)) # 0 è un counter
                except (ValueError, RuntimeError) as e:
                    logging.error(f"[ERROR] Preprocessing fallito: {e}")
                    return None
                
                node_counter = 0
                start_time = time()
                last_log_time = start_time

                while queue:
                    heuristic_lb, lb, _, config, critical_activities = heapq.heappop(queue)
                    self._n_chiamate += 1
    
                    # Log periodico
                    curr_time = time()
                    elapsed = curr_time - start_time
                    if curr_time - last_log_time >= self.log_interval:
                        nodes_per_sec = self._n_chiamate / elapsed if elapsed > 0 else 0
                        open_vars = self._count_open_vars(config)
                        logging.info(
                            f"[PROGRESS] Nodi: {self._n_chiamate} | Coda: {len(queue)} | "
                            f"Best UB: {self._best_ub:.2f} |  LB optimistic: {lb:.2f} | LB euristic: {heuristic_lb:.2f} | "
                            f"Var aperte: {open_vars} | Speed: {nodes_per_sec:.1f} n/s"
                        )
                        last_log_time = curr_time
    
                    # Controllo limiti
                    if self._n_chiamate > self.max_nodes or elapsed > self.max_time:
                        reason = "Limite nodi" if self._n_chiamate > self.max_nodes else "Limite tempo"
                        logging.warning(f"B&B interrotto: {reason}. Miglior UB: {self._best_ub}")
                        break
    
                    # Pruning standard
                    if lb >= self._best_ub:
                        continue
    
                    # CONTROLLO NUMERO VARIABILI APERTE
                    open_vars = self._count_open_vars(config)
    
                    if open_vars == 0:
                        # Foglia: tutti gli intervalli sono stati risolti a scalari
                        fixed = self._fix_config_for_ub(config)
                        start = perf_counter()
                        sol = self._compute_ub(
                            fixed["durations"], fixed["resources"],
                            fixed["release_dates"], fixed["due_dates"]
                        )
                        logging.debug(f"Soluzione UB calcolata in {perf_counter() - start:.2f} secondi")
                        best_inner = sol.get("best", {}).get("best", {})
                        if isinstance(best_inner, dict):
                            ub_score = self._get_score_from_solution(best_inner)
                            if ub_score < self._best_ub:
                                self._best_ub = ub_score
                                start = perf_counter()
                                self._best_config = copy.deepcopy(fixed)
                                self._best_solution_orchestrator = sol
                                logging.debug(f"Configurazione e soluzione salvate con deepcopy in {perf_counter() - start:.2f} secondi")
                                logging.info(f"LEAF #{self._n_chiamate}] Nuovo best UB: {self._best_ub}")
                        continue

                    # -----------------------------------------------------------------
                    # SELEZIONE VARIABILE — FIX 1
                    # Deterministica: dipende SOLO da config e critical_activities,
                    # non da _n_chiamate o altri contatori globali.
                    # -----------------------------------------------------------------
                    start = perf_counter()
                    var = self._select_best_variable(config, critical_activities)
                    logging.debug(f"Selezione variabile completata in {perf_counter() - start:.2f} secondi")
                    field, i = var
                    val = config[field][i]
                    low, high = val
    
                    # -----------------------------------------------------------------
                    # BRANCHING PER SPLITTING — FIX 2
                    # Divide [low, high] in [low, mid] e [mid+1, high].
                    # I sotto-intervalli con un solo elemento diventano scalari.
                    # In questo modo ogni intero è raggiungibile in O(log(high-low)) livelli.
                    # -----------------------------------------------------------------
                    start = perf_counter()
                    left_val, right_val = self._branch_on_interval(low, high)
                    logging.debug(f"Branching per splitting completato in {perf_counter() - start:.2f} secondi")
    
                    for branch_val in (left_val, right_val):
                        start = perf_counter()
                        conf_new = copy.deepcopy(config)
                        conf_new[field][i] = branch_val
                        conf_new = self._normalize_config(conf_new)
                        logging.debug(f"Configurazione copiata con deepcopy per branch e normalizzata in {perf_counter() - start:.2f} secondi")
                        
                        # Descrizione leggibile per il log
                        branch_desc = (
                            f"[{branch_val[0]},{branch_val[1]}]"
                            if isinstance(branch_val, tuple)
                            else str(branch_val)
                        )
    
                        fixed_new = self._fix_config_for_lb(conf_new)
                        fixed_new_mid = self._fix_config_for_lb_mid(conf_new)
                        try:
                            start = perf_counter()
                            proc_new = _pre_processing_rcpsp_max(
                                n=self.base_data.n, durations=fixed_new["durations"],
                                precedences=self.base_data.precedences,
                                resources=fixed_new["resources"],
                                consumption=self.base_data.consumption,
                                horizon=self.base_data.horizon,
                                release_dates=fixed_new["release_dates"],
                                due_dates=fixed_new["due_dates"]
                            )
                            proc_new_mid = _pre_processing_rcpsp_max(
                                n=self.base_data.n, durations=fixed_new_mid["durations"],
                                precedences=self.base_data.precedences,
                                resources=fixed_new_mid["resources"],
                                consumption=self.base_data.consumption,
                                horizon=self.base_data.horizon,
                                release_dates=fixed_new_mid["release_dates"],
                                due_dates=fixed_new_mid["due_dates"]
                            )
                            logging.debug(f"Pre-processing completato in {perf_counter() - start:.2f} secondi")
                            start = perf_counter()
                            optimistic_lb, crit_new = self._compute_lb(
                                proc_new.n, proc_new.durations, proc_new.precedences,
                                proc_new.consumption, proc_new.resources, proc_new.release_dates
                            )
                            heuristic_mid_lb, crit_new_mid = self._compute_lb(
                                proc_new_mid.n, proc_new_mid.durations, proc_new_mid.precedences,
                                proc_new_mid.consumption, proc_new_mid.resources, proc_new_mid.release_dates
                            )
                            logging.debug(f"LB calcolati in {perf_counter() - start:.2f} secondi")
    
                            if optimistic_lb < self._best_ub:
                                node_counter += 1
                                
                                child_open_vars = self._count_open_vars(conf_new)
                                # UB euristico quando il nodo è promettente
                                if optimistic_lb < self._best_ub * 0.9 or child_open_vars < self._variabili_totali_aperte // 2:
                                    start = perf_counter()
                                    sol_heur = self._compute_ub(
                                        fixed_new["durations"], fixed_new["resources"],
                                        fixed_new["release_dates"], fixed_new["due_dates"]
                                    )
                                    logging.debug(f"UB euristico calcolato in {perf_counter() - start:.2f} secondi")
                                    inner_heur = sol_heur.get("best", {}).get("best", {})
                                    if (isinstance(inner_heur, dict)):
                                        heur_score = self._get_score_from_solution(inner_heur)
                                        if heur_score < self._best_ub:
                                            self._best_ub = heur_score
                                            start = perf_counter()
                                            self._best_config = copy.deepcopy(fixed_new)
                                            self._best_solution_orchestrator = sol_heur
                                            logging.debug(f"Configurazione copiata con deepcopy e salvata in {perf_counter() - start:.2f} secondi")
                                            logging.info(
                                                f"[HEUR #{self._n_chiamate}] "
                                                f"Nuovo UB euristico: {self._best_ub}"
                                            )
    
                                heapq.heappush(queue, (heuristic_mid_lb, optimistic_lb, node_counter, conf_new, crit_new_mid))
    
                        except Exception as e:
                            # Infeasible dopo preprocessing → ramo scartato silenziosamente
                            logging.debug(f"[PRUNE] {field}[{i}]={branch_desc} infeasible: {e}")
                            continue
 
                end_time = time()
                logging.info(
                    f"[DONE] Nodi esplorati: {self._n_chiamate} | "
                    f"Tempo: {(end_time - start_time) / 60:.2f} min | "
                    f"Best UB: {self._best_ub}"
                )
                return self.best_solution()
 
    @staticmethod
    def _count_open_vars(config):
        """Restituisce il numero di variabili ancora a intervallo nella config."""
        count = 0
        for field in ("durations", "resources", "release_dates", "due_dates"):
            for val in config[field]:
                if isinstance(val, tuple) and val[0] != val[1]:
                    count += 1
        return count

    def _select_best_variable(self, config, critical_activities):
        """
        Seleziona la variabile (field, index) su cui fare branching.
 
        Criteri in ordine di priorità:
          1. Attività critiche (contribuiscono al makespan LB)
          2. Intervallo più ampio (massima incertezza residua)
          3. Campo con priorità fissa: durations > resources > release_dates > due_dates
             (le durate influenzano CPM più direttamente)
 
        La selezione dipende SOLO dallo stato della config e da critical_activities,
        NON da contatori esterni come _n_chiamate — in questo modo è consistente
        tra nodi fratelli e tra sessioni diverse.
        """
        field_priority = ["durations", "resources", "release_dates", "due_dates"]
 
        best_var = None
        # Tupla di confronto: (is_critical, interval_size, -field_idx)
        # Usiamo -field_idx perché vogliamo preferire indici bassi di field_priority
        best_score = (-1, -1, float("-inf"))
 
        for field_idx, field in enumerate(field_priority):
            for i, val in enumerate(config[field]):
                if not isinstance(val, tuple):
                    continue
                low, high = val
                if high <= low:
                    # Intervallo degenere: sarà normalizzato al prossimo fix, salta
                    continue
                interval_size = high - low
                is_critical = 1 if i in critical_activities else 0
                # Score più alto = variabile più interessante da rompere
                score = (is_critical, interval_size, -field_idx)
                if score > best_score:
                    best_score = score
                    best_var = (field, i)
 
        return best_var
    
    @staticmethod
    def _branch_on_interval(low, high):
        """
        Divide un intervallo intero [low, high] in due rami.
 
        Regole:
          - Se low == high → già scalare, non dovrebbe arrivare qui
          - Se adiacenti (high == low + 1) → due scalari: low, high
          - Altrimenti → (low, mid) e (mid+1, high) dove mid = (low+high)//2
            I valori risultanti sono scalari se il sotto-intervallo ha dimensione 1,
            altrimenti rimangono tuple per il branching successivo.
 
        Questo garantisce che ogni intero in [low, high] sia raggiungibile
        in ceil(log2(high - low + 1)) livelli di profondità.
 
        Esempi:
          [5, 20] → (5,12),  (13,20)   [entrambi intervalli, 2 livelli ancora]
          [5,  6] → 5,       6          [due scalari immediati]
          [5,  7] → (5,6),   7          [intervallo + scalare]
          [7,  7] → non chiamare questa funzione (val già scalare)
        """
        if low == high:
            raise ValueError(f"_branch_on_interval chiamato con intervallo degenere [{low},{high}]")
 
        mid = (low + high) // 2
 
        # Ramo sinistro: [low, mid]
        left = low if mid == low else (low, mid)
 
        # Ramo destro: [mid+1, high]
        right_low = mid + 1
        right = right_low if right_low == high else (right_low, high)
 
        return left, right

    def _estimate_lb_for_config(self, config):
        fixed = self._fix_config_for_lb(config)
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
    
    def _fix_config_for_lb(self, config):
        """Fisso la config per il calcolo del LB. Uso i valori fissati nella config corrente."""
        return{
            "durations": [d if not isinstance(d, tuple) else min(d) for d in config["durations"]],
            "resources": [r if not isinstance(r, tuple) else max(r) for r in config["resources"]],
            "release_dates": [rd if not isinstance(rd, tuple) else min(rd) for rd in config["release_dates"]],
            "due_dates": [dd if not isinstance(dd, tuple) else max(dd) for dd in config["due_dates"]],
        }

    def _fix_config_for_lb_mid(self, config):
        """Fisso la config per il calcolo del LB. Uso i valori medi delle tuple."""
        return{
            "durations": [d if not isinstance(d, tuple) else (d[0] + d[1]) // 2 for d in config["durations"]],
            "resources": [r if not isinstance(r, tuple) else (r[0] + r[1]) // 2 for r in config["resources"]],
            "release_dates": [rd if not isinstance(rd, tuple) else (rd[0] + rd[1]) // 2 for rd in config["release_dates"]],
            "due_dates": [dd if not isinstance(dd, tuple) else (dd[0] + dd[1]) // 2 for dd in config["due_dates"]],
        }
    
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

        # I max_lag implicano che start_j <= start_i + max_lag
        # Questo si traduce in: start_i >= start_j - max_lag
        # Aggiungere arco inverso con peso -max_lag per propagare il vincolo
        for (i, j, min_lag, max_lag) in precedences:
            G.add_edge(i, j, weight=min_lag)
            if max_lag is not None:
                # start_j <= start_i + max_lag  =>  start_i >= start_j - max_lag
                G.add_edge(j, i, weight=-max_lag)

        for i in activities:
            if i != 0 and release_dates[i] is not None:
                rd = release_dates[i]
                if G.has_edge(0, i):
                    G[0][i]["weight"] = max(G[0][i]["weight"], rd)
                else:
                    G.add_edge(0, i, weight=rd)
        
        try:
            # Per il calcolo del Longest Path con cicli (possibili in RCPSP/Max),
            # usiamo Bellman-Ford su pesi negati: LP(u,v,w) = -SP(u,v,-w).
            G_neg = nx.DiGraph()
            for u, v, data in G.edges(data=True):
                G_neg.add_edge(u, v, weight=-data['weight'])
            
            # Calcolo dei cammini minimi sul grafo negato
            neg_dist = nx.single_source_bellman_ford_path_length(G_neg, 0)
            
            # Ricostruiamo le distanze originali (negando i risultati)
            # Inizializziamo a float("-inf") per attività non raggiungibili
            dist = {act: float("-inf") for act in activities}
            for act, d in neg_dist.items():
                dist[act] = -d

        except (nx.NetworkXUnbounded, nx.NegativeCycle):
            raise ValueError("Il grafo contiene un ciclo a peso positivo (inconsistenza temporale).")
        except Exception as e:
            raise ValueError(f"Errore nel calcolo del CPM: {e}")

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

    @staticmethod
    def _get_score_from_solution(sol_dict):
        """Estrae lo score dalla soluzione, usando il makespan come fallback."""
        score = sol_dict.get("score")
        if score is None:
            score = sol_dict.get("makespan")
        return float(score) if score is not None else float("inf")

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

    @staticmethod
    def _normalize_config(config):
        out = copy.deepcopy(config)

        for field in ("durations", "resources", "release_dates", "due_dates"):
            for i, val in enumerate(out[field]):
                if isinstance(val, tuple):
                    low, high = val
                    if low == high:
                        out[field][i] = low

        return out

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
    
    @staticmethod
    def _open_log_file():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"solver/logs/branch_and_bound_{ts}.log"
        
        logging.basicConfig(
            filename=filename,
            filemode='a',
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            force=True
        )