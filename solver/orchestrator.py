"""
orchestrator.py
-----------------
Implementazione dell'orchestratore che elabora i dati in input e chiama 
i moduli appropriati per risolvere le istanze dei problemi.

In questo modulo è implementato il sistema decisionale, che sceglie quali
modelli andare a utilizzare in base ai parametri dell'utente e ad altri
fattori legati all'istanza del problema.

La classe fa delle stime sulla difficoltà del problema e possibile tempo di
esecuzione.

Il modulo mette a disposizione anche una struttura in grado di esplorare 
diverse soluzioni in base alla combinazioni di dati nel caso in cui ci siano
dei vincoli più rilassati. Ad esempio, durations[i] potrebbe essere un intervallo
e non una data specifica, per questo motivo, l'orchestrator deve cercare la migliore
soluzione lanciando più volte il modello scelto.
"""
from solver.preprocessing import _pre_processing_rcpsp_max, _pre_processing_rcpsp
from solver.builders import _run_sgs, _run_exact_model
from solver.branch_and_bound import BranchAndBoundSolver
from solver.dataclasses.input_data import InputData
from solver.dataclasses.soluzione_orchestrator import SolutionDTO, RankingDTO

class SolverOrchestrator:

    def __init__(self):
        """
        Inizializza un'istanza di SolverOrchestrator.
        
        Questa classe gestisce l'orchestrazione della risoluzione di problemi di scheduling
        (RCPSP e RCPSP_MAX) scegliendo automaticamente il modello più appropriato.
        
        Attributi:
            _n: Numero totale di attività (incluse dummy)
            _activities: Lista delle attività
            _durations: Lista delle durate delle attività
            _precedences: Lista delle precedenze tra attività
            _resources: Lista delle disponibilità delle risorse
            _consumption: Matrice dei consumi di risorse per attività
            _horizon: Orizzonte temporale massimo
            _release_dates: Date di inizio disponibilità attività (RCPSP_MAX)
            _due_dates: Date di scadenza delle attività (RCPSP_MAX)
        """
        self._n = None
        self._activities = None
        self._durations = None
        self._precedences = None
        self._resources = None
        self._consumption = None
        self._horizon = None
        self._release_dates = None
        self._due_dates = None
    
    #————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
    # SISTEMA DECISIONALE
    #————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————

    def choose_model(self, n: int = None, durations: list[int | tuple[int, int]] = None, precedences: list[tuple[int,int,str,int,int | None]] | list[tuple[int,int]] = None, resources: list[int | tuple[int, int]] = None, 
                     consumption: list[list[int]] = None, horizon: int = None, release_dates: list[int | tuple[int, int]] = None, due_dates: list[int | tuple[int, int]] = None, top_k: int = 5, time_weight: float = 1, resource_weight: float = 1, 
                     priority_weight: float = 1, tardiness_weight: float = 1, limit_lookahead: int = 5, instant_sol: bool = False, priority_rule: str = None, rcpsp_max: bool = False, has_intervals: bool = False, max_nodes: int = 5000, max_time: int = 600,
                     input_data: InputData = None) -> SolutionDTO:
        """
        Esegue il preprocessing dei dati e sceglie il modello più appropriato (esatto o euristico)
        in base ai parametri ricevuti dall'utente e alla difficoltà stimata dell'istanza.
        La scelta tra modelli esatti e euristici, nonché la configurazione degli euristici,
        è automatica e basata su metriche dell'istanza per garantire un equilibrio tra qualità
        della soluzione e tempo di esecuzione.
        
        Args:
            n: Numero di attività
            durations: Lista delle durate
            precedences: Lista delle precedenze (FS,SS,FF,SF per RCPSP_MAX oppure semplici coppie per RCPSP)
            resources: Liste delle disponibilità di risorse
            consumption: Matrice dei consumi di risorse
            horizon: Limite temporale
            release_dates: Date di disponibilità (opzionale, per RCPSP_MAX)
            due_dates: Date di scadenza (opzionale, per RCPSP_MAX)
            top_k: Numero di soluzioni top da mantenere nel ranking
            time_weight: Peso del makespan nella funzione obiettivo (RCPSP_MAX)
            resource_weight: Peso dell'utilizzo di risorse (RCPSP_MAX)
            priority_weight: Peso delle priorità (RCPSP_MAX)
            tardiness_weight: Peso del tardiness (RCPSP_MAX)
            limit_lookahead: Profondità di lookahead per l'algoritmo SGS (RCPSP_MAX)
            instant_sol: Se True, esegue euristici veloci; se False, cerca soluzione esatta
            priority_rule: Regola di priorità da usare negli euristici (opzionale)
            rcpsp_max: True per risolvere RCPSP_MAX, False per RCPSP
            has_intervals: Indica se le durate, risorse, date di rilascio o date di scadenza sono fornite come intervalli 
            invece che come valori fissi (in questo caso, viene eseguita una ricerca più ampia per trovare la soluzione migliore)
            
        Returns:
            Dizionario con chiavi:
                - 'type': Tipo di modello usato ('exact', 'heuristic_single_start', 'heuristic_multi_start', 'heuristic_fallback')
                - 'problem_difficulty': Difficoltà stimata ('easy', 'medium', 'hard')
                - 'results': Dettagli computazionali (None per exact)
                - 'best': Soluzione migliore trovata
        """
        preprocessing = False
        if input_data:
            n = n or input_data.n
            durations = durations or input_data.durations
            precedences = precedences or input_data.precedences
            resources = resources or input_data.resources
            consumption = consumption or input_data.consumption
            horizon = horizon or input_data.horizon
            release_dates = release_dates or input_data.release_dates
            due_dates = due_dates or input_data.due_dates
            # Aggiorno i parametri dell'orchestrator/solver dai campi di input_data se non passati esplicitamente
            # (Assumiamo che se i parametri sono diversi dai default, l'utente li ha passati)
            # Per semplicità, se input_data è presente, usiamo i suoi valori per i pesi se non diversamente specificato
            top_k = top_k if top_k != 5 else input_data.top_k
            time_weight = time_weight if time_weight != 1 else input_data.time_weight
            resource_weight = resource_weight if resource_weight != 1 else input_data.resource_weight
            priority_weight = priority_weight if priority_weight != 1 else input_data.priority_weight
            tardiness_weight = tardiness_weight if tardiness_weight != 1 else input_data.tardiness_weight
            limit_lookahead = limit_lookahead if limit_lookahead != 5 else input_data.limit_lookahead
            instant_sol = instant_sol if instant_sol else input_data.instant_sol
            priority_rule = priority_rule or input_data.priority_rule
            rcpsp_max = rcpsp_max if rcpsp_max else input_data.rcpsp_max
            has_intervals = has_intervals if has_intervals else input_data.has_intervals

            max_nodes = max_nodes if max_nodes != 5000 else input_data.max_nodes
            max_time = max_time if max_time != 600 else input_data.max_time

        if has_intervals:
            config = {
                "n": n,
                "durations": durations,
                "precedences": precedences,
                "resources": resources,
                "consumption": consumption,
                "horizon": horizon,
                "release_dates": release_dates,
                "due_dates": due_dates,
                "top_k": top_k,
                "time_weight": time_weight,
                "resource_weight": resource_weight,
                "priority_weight": priority_weight,
                "tardiness_weight": tardiness_weight,
                "limit_lookahead": limit_lookahead,
                "instant_sol": instant_sol,
                "priority_rule": priority_rule,
                "rcpsp_max": rcpsp_max,
                "max_nodes": max_nodes,
                "max_time": max_time,
            }
            
            if input_data:
                # Se abbiamo input_data, lo passiamo direttamente
                # ma aggiorniamo i suoi campi se sono stati cambiati via argomenti
                for key, value in config.items():
                    if hasattr(input_data, key):
                        setattr(input_data, key, value)
                b_and_b = BranchAndBoundSolver(self, input_data=input_data)
            else:
                b_and_b = BranchAndBoundSolver(self, **config)
            
            b_and_b.esplora_soluzioni(instant_sol, rcpsp_max)
            best_solution = b_and_b.best_solution()
            if best_solution is None:
                raise RuntimeError("Il branch and bound non ha trovato una soluzione fattibile.")
            
            return best_solution
        if rcpsp_max:
            try:
                processed = _pre_processing_rcpsp_max(n, durations, precedences, resources, consumption, horizon, release_dates, due_dates)
                preprocessing = True
            except Exception as e:
                raise e
        else:
            try:
                processed = _pre_processing_rcpsp(n, durations, precedences, resources, consumption, horizon)
                preprocessing = True
            except Exception as e:
                raise e

        if not preprocessing:
            raise RuntimeError("Attenzione! Devi elaborare i dati con la funzione di pre processing adatta prima di scegliere il modello.")
        
        self._n = processed.n
        self._activities = processed.activities
        self._durations = processed.durations
        self._precedences = processed.precedences
        self._resources = processed.resources
        self._consumption = processed.consumption
        self._horizon = processed.horizon
        if rcpsp_max:
            self._release_dates = processed.release_dates
            self._due_dates = processed.due_dates
        
        diff = self._calcola_diff()
    
        if rcpsp_max:
            self._time_weight = time_weight
            self._resource_weight = resource_weight
            self._priority_weight = priority_weight
            self._tardiness_weight = tardiness_weight
            self._limit_lookahead = limit_lookahead

        # CASO 1
        # Soluzione veloce richiesta
        if instant_sol:
            # Lancio euristiche
            if diff == "easy":
                # In questo caso una singola run basta
                all_results, best_solution, _ = _run_sgs(
                    self,
                    rcpsp_max=rcpsp_max,
                    mode="single_start",
                    rule=priority_rule,
                    top_k=top_k,
                )
                return SolutionDTO(
                    type="heuristic_single_start",
                    problem_difficulty=diff,
                    problem_type="RCPSP_MAX" if rcpsp_max else "RCPSP",

                    ranking=RankingDTO(
                        best_solution=best_solution.get("best"),
                        top_k_makespan=best_solution.get("top_k_makespan"),
                        top_k_score=best_solution.get("top_k_score"),
                    ),

                    results=all_results,
                )
            elif diff == "medium":
                # In questo caso meglio il multistart soft
                all_results, best_solution, _ = _run_sgs(
                    self,
                    rcpsp_max=rcpsp_max,
                    mode="multi_start",
                    rule=None,
                    n_runs=50,
                    top_k=top_k,
                )
                return SolutionDTO(
                    type="heuristic_multi_start",
                    problem_difficulty=diff,
                    problem_type="RCPSP_MAX" if rcpsp_max else "RCPSP",

                    ranking=RankingDTO(
                        best_solution=best_solution.get("best"),
                        top_k_makespan=best_solution.get("top_k_makespan"),
                        top_k_score=best_solution.get("top_k_score"),
                    ),

                    results=all_results,
                )
            else:
                # In questo caso eseguo un multistart hard
                all_results, best_solution, _ = _run_sgs(
                    self,
                    rcpsp_max=rcpsp_max,
                    mode="multi_start",
                    rule=None,
                    n_runs=500,
                    top_k=top_k,
                )
                return SolutionDTO(
                    type="heuristic_multi_start",
                    problem_difficulty=diff,
                    problem_type="RCPSP_MAX" if rcpsp_max else "RCPSP",

                    ranking=RankingDTO(
                        best_solution=best_solution.get("best"),
                        top_k_makespan=best_solution.get("top_k_makespan"),
                        top_k_score=best_solution.get("top_k_score"),
                    ),

                    results=all_results,
                )
        # CASO 2
        # Soluzione esatta o normale richiesta
        else:
            # Lancio metodo esatto
            try:
                solution = _run_exact_model(self, rcpsp_max=rcpsp_max, max_time=max_time)
                return SolutionDTO(
                    type="exact",
                    problem_difficulty=diff,
                    problem_type="RCPSP_MAX" if rcpsp_max else "RCPSP",

                    ranking=RankingDTO(
                        best_solution=solution,
                        top_k_makespan=[solution],
                        top_k_score=[]
                    ),

                    results=None,
                )

            except Exception as e:
                print(e)
                print("Il modello esatto non ha trovato una soluzione ottimale o fattibile, eseguo fallback con euristiche...")
                all_results, best_solution, _ = _run_sgs(self, rcpsp_max=rcpsp_max, mode="multi_start", rule=None, n_runs=500, top_k=top_k)
                return SolutionDTO(
                    type="heuristic_fallback",
                    problem_difficulty=diff,
                    problem_type="RCPSP_MAX" if rcpsp_max else "RCPSP",

                    ranking=RankingDTO(
                        best_solution=best_solution.get("best"),
                        top_k_makespan=best_solution.get("top_k_makespan"),
                        top_k_score=best_solution.get("top_k_score"),
                    ),

                    results=all_results,
                )

    def _calcola_diff(self):
        """
        Stima la difficoltà computazionale dell'istanza del problema.
        
        Calcola un score basato su 6 metriche caratteristiche dell'istanza:
        1. Densità del grafo delle precedenze
        2. Criticità delle risorse (tightness)
        3. Variabilità delle durate
        4. Squilibrio nell'utilizzo delle risorse
        5. Pressione temporale (rapporto durata totale / horizon)
        6. Dimensione del problema
        
        Queste metriche sono combinate in uno score finale che classifica il problema
        in categorie: easy (score <= 3), medium (score <= 7), hard (score > 7).
        
        Returns:
            Stringa tra 'easy', 'medium', 'hard' che rappresenta la difficoltà stimata
        """
        n = self._n
        m = len(self._precedences)
        R = len(self._resources)

        if n <= 2:
            return "easy"

        # 1) Densità grafo
        density = m / n

        # 2) Resource tightness
        total_demand = 0
        for i in range(1, n - 1):
            duration = self._durations[i]
            for r in range(R):
                total_demand += self._consumption[i][r] * duration

        total_capacity = sum(self._resources) * self._horizon
        resource_tightness = total_demand / total_capacity if total_capacity > 0 else 0

        # 3) Variabilità durate
        avg_dur = sum(self._durations) / n
        variance = sum((d - avg_dur) ** 2 for d in self._durations) / n
        duration_cv = (variance ** 0.5) / avg_dur if avg_dur > 0 else 0

        # 4) Resource imbalance
        # misura quanto una risorsa è "collo di bottiglia"
        resource_usage = [0] * R
        for i in range(1, n - 1):
            for r in range(R):
                resource_usage[r] += self._consumption[i][r]

        total_usage = sum(resource_usage)
        imbalance = max(resource_usage) / (total_usage / R) if (R > 0 and total_usage > 0) else 0

        # 5) Time pressure
        total_duration = sum(self._durations)
        time_pressure = total_duration / self._horizon if self._horizon > 0 else 0

        # SCORE, calcolato in base ai parametri sopra definiti
        score = 0

        # dimensione
        if n > 80:
            score += 3
        elif n > 40:
            score += 2
        elif n > 20:
            score += 1

        # densità
        if density > 5:
            score += 3
        elif density > 3:
            score += 2
        elif density > 2:
            score += 1

        # risorse
        if resource_tightness > 0.85:
            score += 3
        elif resource_tightness > 0.7:
            score += 2
        elif resource_tightness > 0.5:
            score += 1

        # pressione temporale
        if time_pressure > 1.2:
            score += 3
        elif time_pressure > 0.9:
            score += 2
        elif time_pressure > 0.7:
            score += 1

        # variabilità
        if duration_cv > 1:
            score += 2
        elif duration_cv > 0.5:
            score += 1

        # imbalance risorse
        if imbalance > 2:
            score += 2
        elif imbalance > 1.5:
            score += 1

        # CLASSIFICAZIONE
        if score <= 3:
            return "easy"
        elif score <= 7:
            return "medium"
        else:
            return "hard"

if __name__ == '__main__':
    from tests.instance_rcpsp_and_rcpsp_max import Instance

    n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, horizon, consumption, release_dates, due_dates = Instance.get_raw_instance()
    top_k = 5

    so = SolverOrchestrator()

    # soluzione = so.choose_model(n, durations, precedences_rcpsp_max, resources, consumption, horizon, release_dates, due_dates, instant_sol=False, rcpsp_max=True, top_k=top_k)
    # soluzione = so.choose_model(n, durations, precedences_rcpsp, resources, consumption, horizon, instant_sol=True, rcpsp_max=False, top_k=top_k)
    soluzione = so.choose_model(n, durations, precedences_rcpsp_max, resources, consumption, horizon, release_dates, due_dates, instant_sol=True, rcpsp_max=True, top_k=top_k)
    
    type_exact = (soluzione.solution_type == "exact")

    type_rcpsp_max = (
        soluzione.problem_type == "RCPSP_MAX"
    )

    print("=======================================================")
    print(f"Metodo utilizzato: {soluzione.solution_type}")
    print(f"Difficoltà del problema stimata: {soluzione.problem_difficulty}")

    if soluzione.results is not None:
        print(f"Risultati: {soluzione.results}")

    print(f"Soluzione migliore: {soluzione.ranking.best_solution}")

    if not type_exact:

        if type_rcpsp_max:

            print(f"\nAltre top {top_k-1} soluzioni ordinate per score:")

            for elem in soluzione.ranking.top_k_score[1:top_k]:
                print(elem)

            print(f"\nAltre top {top_k-1} soluzioni ordinate per makespan:")

            for elem in soluzione.ranking.top_k_makespan[1:top_k]:
                print(elem)

        else:

            print(f"\nAltre top {top_k-1} soluzioni:")

            for elem in soluzione.ranking.top_k_makespan[1:top_k]:
                print(elem)

    print("==============================================================================================================")

    # Test per Branch and Bound

    n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, horizon, consumption, release_dates, due_dates = Instance.get_raw_instance_with_intervals_minimal()
    top_k = 5

    print("\n")
    print("==============================================================================================================")

    soluzione = so.choose_model(n, durations, precedences_rcpsp_max, resources, consumption, horizon, release_dates, due_dates, instant_sol=True, rcpsp_max=True, top_k=top_k, has_intervals=True)

    type_rcpsp_max = (
        soluzione.problem_type == "RCPSP_MAX"
    )

    print("Branch and Bound chiamato correttamente!")
    print("=======================================================")

    print(f"Metodo utilizzato: {soluzione.solution_type}\n")

    print(
        f"Difficoltà del problema stimata: "
        f"{soluzione.problem_difficulty}\n"
    )

    if soluzione.results is not None:
        print(f"Risultati: {soluzione.results}\n")

    print(
        f"Soluzione migliore: "
        f"{soluzione.ranking.best_solution}"
    )

    if type_rcpsp_max:

        print(f"\nAltre top {top_k-1} soluzioni ordinate per score:")

        for elem in soluzione.ranking.top_k_score[1:top_k]:
            print(elem)

        print(f"\nAltre top {top_k-1} soluzioni ordinate per makespan:")

        for elem in soluzione.ranking.top_k_makespan[1:top_k]:
            print(elem)

    else:

        print(f"\nAltre top {top_k-1} soluzioni:")

        for elem in soluzione.ranking.top_k_makespan[1:top_k]:
            print(elem)

    print("\n")
    print(
        "La configurazione migliore presa in considerazione è:"
    )
    print(
        soluzione.additional_info["best_config"]
    )
    print("=======================================================")