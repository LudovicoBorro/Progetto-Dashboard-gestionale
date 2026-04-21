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
from utils.validators.validate_input_rcpsp import validate_inputs as val_inputs_rcpsp
from utils.validators.validate_input_rcpsp_max import validate_inputs as val_inputs_rcpsp_max
from core.heuristics.sgs_engine_rcpsp_max import SGSEngine as SGSEngineMax
from core.heuristics.sgs_engine_rcpsp import SGSEngine
from core.heuristics.multistart_rcpsp import get_best_solution_overall as best_solution_rcpsp
from core.heuristics.multistart_rcpsp_max import get_best_solution_overall as best_solution_rcpsp_max
from core.exact.rcpsp import Model as RCPSPModel
from core.exact.rcpsp_max import Model as RCPSPMaxModel

class SolverOrchestrator:

    def __init__(self):
        self._n = None
        self._activities = None
        self._durations = None
        self._precedences = None
        self._resources = None
        self._consumption = None
        self._horizon = None
        self._release_dates = None
        self._due_dates = None
        self._prepocessing = False
        self._rcpsp_max = False

    #————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
    # PREPROCESSING DEGLI INPUT PER COMPATIBILITÀ MODELLI
    #————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————

    def pre_processing_rcpsp(self, n: int, durations: list[int], precedences: list[tuple[int,int]], resources: list[int], 
                             consumption: list[list[int]], horizon: int):
        
        self._prepocessing = False
        
        # Aggiungo le attività dummy, quella iniziale e finale
        self._n = n + 2
        self._activities = list(range(self._n))
        self._durations = [0] + durations + [0]
        self._resources = resources
        lista_consumi = [0] * len(self._resources)
        self._consumption = [lista_consumi.copy()] + consumption + [lista_consumi.copy()]
        self._horizon = horizon
        precedences = self._shift_precedences(precedences, rcpsp_max=False)
        precedences = self._add_dummy_activities(precedences=precedences, rcpsp_max=False)
        self._precedences = precedences

        # Lancio una validazione dei dati processati
        try:
            val_inputs_rcpsp(self)
        except Exception as e:
            raise e
        
        self._prepocessing = True

    def pre_processing_rcpsp_max(self,  n: int, durations: list[int], precedences: list[tuple[int,int,str,int,int | None]], resources: list[int], 
                                 consumption: list[list[int]], horizon: int, release_dates: list[int], due_dates: list[int]):
        
        self._prepocessing = False
        
        # Aggiungo le attività dummy, quella iniziale e finale
        self._n = n + 2
        self._activities = list(range(self._n))
        self._durations = [0] + durations + [0]
        self._resources = resources
        lista_consumi = [0] * len(self._resources)
        self._consumption = [lista_consumi.copy()] + consumption + [lista_consumi.copy()]
        self._horizon = horizon
        self._release_dates = [None] + release_dates + [None]
        self._due_dates = [None] + due_dates + [None]
        precedences = self._shift_precedences(precedences, rcpsp_max=True)
        precedences = self._convert_precedences_to_minmax(precedences, self._durations)
        precedences = self._add_dummy_activities(precedences=precedences, rcpsp_max=True)
        self._precedences = precedences

        # Lancio una validazione dei dati processati
        try:
            val_inputs_rcpsp_max(self)
        except Exception as e:
            raise e
        
        self._prepocessing = True
        self._rcpsp_max = True

    def _convert_precedences_to_minmax(self, precedences, durations) -> list[tuple[int, int, int, int | None]]:
        result = []

        for (i, j, type, lag, max_lag) in precedences:

            if type == "FS":
                min_lag = durations[i] + lag
                max_lag_conv = durations[i] + max_lag if max_lag is not None else None

            elif type == "SS":
                min_lag = lag
                max_lag_conv = max_lag

            elif type == "FF":
                min_lag = durations[i] - durations[j] + lag
                max_lag_conv = durations[i] - durations[j] + max_lag if max_lag is not None else None

            elif type == "SF":
                min_lag = -durations[j] + lag
                max_lag_conv = -durations[j] + max_lag if max_lag is not None else None

            else:
                raise ValueError(f"Tipo precedenza non supportato: {type}")

            result.append((i, j, min_lag, max_lag_conv))

        return result
    
    def _add_dummy_activities(self, precedences, rcpsp_max: bool):
        new_precedences = []

        has_pred = {j: False for j in range(self._n)}
        has_succ = {i: False for i in range(self._n)}

        if rcpsp_max: 
            for (i, j, min_lag, max_lag) in precedences:
                has_pred[j] = True
                has_succ[i] = True

            # dummy start = 0
            for j in range(1, self._n - 1):
                if not has_pred[j]:
                    new_precedences.append((0, j, 0, None))

            # dummy end = n-1
            for i in range(1, self._n - 1):
                if not has_succ[i]:
                    new_precedences.append((i, self._n - 1, self._durations[i], None))
        else:
            for (i, j) in precedences:
                has_pred[j] = True
                has_succ[i] = True

            # dummy start = 0
            for j in range(1, self._n - 1):
                if not has_pred[j]:
                    new_precedences.append((0, j))

            # dummy end = n-1
            for i in range(1, self._n - 1):
                if not has_succ[i]:
                    new_precedences.append((i, self._n - 1))

        return precedences + new_precedences

    def _shift_precedences(self, precedences, rcpsp_max: bool):
        shifted = []

        if rcpsp_max:
            for p in precedences:
                i, j = p[0], p[1]
                rest = p[2:]

                shifted.append((i+1, j+1, *rest))
        else:
            for p in precedences:
                i, j = p[0], p[1]

                shifted.append((i+1, j+1))

        return shifted
    
    #————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
    # SISTEMA DECISIONALE
    #————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————

    def choose_model(self, instant_sol: bool = False, priority_rule: str = None, time_weight: float = 1, resource_weight: float = 1, 
                     priority_weight: float = 1, tardiness_weight: float = 1, limit_lookahead: int = 5):
        """
        Funzione principale del sistema decisionale.
        
        Sceglie il modello da lanciare in base ai parametri ricevuti dall'utente e
        alla difficoltà dell'istanza.
        """
        if not self._prepocessing:
            raise RuntimeError("Attenzione! Devi elaborare i dati con la funzione di pre processing adatta prima di scegliere il modello.")
        
        diff = self._calcola_diff()

        if self._rcpsp_max:
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
                all_results, best_solution = self._run_sgs(
                    mode="single_start",
                    rule=priority_rule,
                )
                return {"type": "heuristic_single_start", "problem_difficulty": diff,
                         "results": all_results, "best_solution": best_solution}
            elif diff == "medium":
                # In questo caso meglio il multistart soft
                all_results, best_solution = self._run_sgs(
                    mode="multi_start",
                    rule=None,
                    n_runs=50,
                )
                return {"type": "heuristic_multi_start", "problem_difficulty": diff,
                         "results": all_results, "best_solution": best_solution}
            else:
                # In questo caso eseguo un multistart hard
                all_results, best_solution = self._run_sgs(
                    mode="multi_start",
                    rule=None,
                    n_runs=500,
                )
                return {"type": "heuristic_multi_start", "problem_difficulty": diff,
                         "results": all_results, "best_solution": best_solution}
        # CASO 2
        # Soluzione esatta o normale richiesta
        else:
            # Lancio metodo esatto
            try:
                solution = self._run_exact_model()
                return {"type": "exact", "solution": solution}
            except Exception:
                all_results, best_solution = self._run_sgs(mode="multi_start", rule=None, n_runs=500)
                return {"type": "heuristic_fallback", "results": all_results, "best": best_solution}

    def _calcola_diff(self):

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

        imbalance = max(resource_usage) / (sum(resource_usage)/R) if R > 0 else 0

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

    def _run_sgs(self, mode = None, rule = None, n_runs = 1):

        sgs = self._build_sgs()

        if self._rcpsp_max:
            precedences_rcpsp_max = self._precedences
            precedences_rcpsp = [(i, j) for (i, j, _, _) in precedences_rcpsp_max]
            if mode == "single_start":
                return best_solution_rcpsp_max(sgs, self._n, self._durations, precedences_rcpsp=precedences_rcpsp, precedences_rcpsp_max=precedences_rcpsp_max,
                                               resources=self._resources, consumption=self._consumption, horizon=self._horizon, time_weight=self._time_weight,
                                               resource_weight=self._resource_weight, priority_weight=self._priority_weight, tardiness_weight=self._tardiness_weight,
                                               limit_lookahead=self._limit_lookahead, n_runs=1, regola=rule)
            elif mode == "multi_start":
                return best_solution_rcpsp_max(sgs, self._n, self._durations, precedences_rcpsp=precedences_rcpsp, precedences_rcpsp_max=precedences_rcpsp_max,
                                               resources=self._resources, consumption=self._consumption, horizon=self._horizon, time_weight=self._time_weight,
                                               resource_weight=self._resource_weight, priority_weight=self._priority_weight, tardiness_weight=self._tardiness_weight,
                                               limit_lookahead=self._limit_lookahead, n_runs=n_runs, regola=rule)
        else:
            if mode == "single_start":
                return best_solution_rcpsp(sgs, self._n, self._durations, self._precedences, self._resources,
                                           self._consumption, self._horizon, n_runs=1, regola=rule)
            elif mode == "multi_start":
                return best_solution_rcpsp(sgs, self._n, self._durations, self._precedences, self._resources,
                                           self._consumption, self._horizon, n_runs=n_runs, regola=rule)

    def _build_sgs(self):
        if self._rcpsp_max:
            return SGSEngineMax(self._n, self._durations, self._precedences, self._resources,
                               self._consumption, self._horizon, self._release_dates, self._due_dates, validate_input=True)
        else:
            return SGSEngine(self._n, self._durations, self._precedences, self._resources, self._consumption, self._horizon, validate_input=True)
        
    def _run_exact_model(self):
        
        model = self._build_exact_model()

        return model.get_final_solution()

    def _build_exact_model(self):
        if self._rcpsp_max:
            return RCPSPMaxModel(self._n, self._durations, self._resources,
                                 self._consumption, self._precedences, self._horizon,
                                 self._release_dates, self._due_dates, validate_input=True)
        else:
            return RCPSPModel(self._n, self._durations, self._precedences, self._resources,
                              self._consumption, self._horizon, validate_input=True)