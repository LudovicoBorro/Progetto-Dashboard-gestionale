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
    # PREPROCESSING DEGLI INPUT PER COMPATIBILITÀ MODELLI
    #————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————

    def _pre_processing_rcpsp(self, n: int, durations: list[int], precedences: list[tuple[int,int]], resources: list[int], 
                             consumption: list[list[int]], horizon: int):
        """
        Preprocessing dei dati di input per il problema RCPSP.
        
        Trasforma i dati forniti dall'utente nel formato interno richiesto dal modello.
        Aggiunge le attività dummy iniziale e finale, effettua lo shift degli indici
        per adattarsi alla numerazione interna, e valida i dati processati.
        
        Args:
            n: Numero di attività (senza dummy)
            durations: Lista delle durate di ciascuna attività
            precedences: Lista di tuple (i,j) che rappresentano le precedenze
            resources: Lista delle disponibilità di ciascuna risorsa
            consumption: Matrice dei consumi di risorse per attività
            horizon: Limite temporale per il completamento del progetto
            
        Raises:
            RuntimeError: Se le precedenze hanno un formato errato
            Exception: Se la validazione dei dati fallisce
        """
        for elem in precedences:
            if len(elem) != 2:
                raise RuntimeError("Le precedenze passate hanno un formato errato!")
        
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

    def _pre_processing_rcpsp_max(self,  n: int, durations: list[int], precedences: list[tuple[int,int,str,int,int | None]], resources: list[int], 
                                 consumption: list[list[int]], horizon: int, release_dates: list[int], due_dates: list[int]):
        """
        Preprocessing dei dati di input per il problema RCPSP_MAX.
        
        Estende il preprocessing RCPSP per gestire vincoli aggiuntivi come date di inizio
        e scadenza, e precedenze di tipo minmax (FS, SS, FF, SF) con lag minimo e massimo.
        
        Args:
            n: Numero di attività (senza dummy)
            durations: Lista delle durate di ciascuna attività
            precedences: Lista di tuple (i,j,tipo,lag,lag_max) dove tipo è uno tra FS,SS,FF,SF
            resources: Lista delle disponibilità di ciascuna risorsa
            consumption: Matrice dei consumi di risorse per attività
            horizon: Limite temporale per il completamento del progetto
            release_dates: Data di disponibilità di ciascuna attività
            due_dates: Data di scadenza di ciascuna attività
            
        Raises:
            RuntimeError: Se le precedenze hanno un formato errato
            Exception: Se la validazione dei dati fallisce
        """
        for elem in precedences:
            if len(elem) != 5:
                raise RuntimeError("Le precedenze passate hanno un formato errato!")
        
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

    def _convert_precedences_to_minmax(self, precedences, durations) -> list[tuple[int, int, int, int | None]]:
        """
        Converte le precedenze da formato testuale (FS,SS,FF,SF) al formato interno minmax.
        
        Trasforma le precedenze notazionali standard (FinishStart, StartStart, FinishFinish, StartFinish)
        in vincoli minmax (lag_min, lag_max) utilizzando le durate delle attività.
        Questo è necessario per convertire i vincoli logici in vincoli temporali numerici.
        
        Args:
            precedences: Lista di tuple (i,j,tipo,lag,lag_max)
            durations: Lista delle durate delle attività (per il calcolo dei lag)
            
        Returns:
            Lista di tuple (i, j, lag_minimo, lag_massimo)
            
        Raises:
            ValueError: Se il tipo di precedenza non è supportato
        """
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
        """
        Aggiunge le attività dummy (inizio e fine) al grafo delle precedenze.
        
        Le attività dummy sono necessarie per rappresentare il punto di inizio e il punto di fine
        di tutto il progetto. Connette tutte le attività senza predecessori alla dummy iniziale
        e tutte le attività senza successori alla dummy finale.
        Questo garantisce una struttura di grafo valida per gli algoritmi di scheduling.
        
        Args:
            precedences: Lista delle precedenze (già shiftate)
            rcpsp_max: True se il problema è RCPSP_MAX, False se RCPSP
            
        Returns:
            Lista aggiornata delle precedenze con i collegamenti alle dummy aggiunti
        """
        new_precedences = []

        has_pred = dict.fromkeys(range(self._n), False)
        has_succ = dict.fromkeys(range(self._n), False)

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
        """
        Effettua lo shift degli indici delle precedenze di +1.
        
        Questa operazione è necessaria perché l'utente fornisce attività numerati da 0,
        ma internamente la dummy iniziale occupa l'indice 0. Pertanto tutti gli indici
        delle attività devono essere shiftati di +1.
        
        Args:
            precedences: Lista delle precedenze originali (numerazione utente 0-based)
            rcpsp_max: True se il problema è RCPSP_MAX, False se RCPSP
            
        Returns:
            Lista delle precedenze con indici shiftati di +1
        """
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

    def choose_model(self, n: int, durations: list[int], precedences: list[tuple[int,int,str,int,int | None]] | list[tuple[int,int]], resources: list[int], 
                     consumption: list[list[int]], horizon: int, release_dates: list[int] = None, due_dates: list[int] = None, top_k: int = 5, time_weight: float = 1, resource_weight: float = 1, 
                     priority_weight: float = 1, tardiness_weight: float = 1, limit_lookahead: int = 5, instant_sol: bool = False, priority_rule: str = None, rcpsp_max: bool = False):
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
            
        Returns:
            Dizionario con chiavi:
                - 'type': Tipo di modello usato ('exact', 'heuristic_single_start', 'heuristic_multi_start', 'heuristic_fallback')
                - 'problem_difficulty': Difficoltà stimata ('easy', 'medium', 'hard')
                - 'results': Dettagli computazionali (None per exact)
                - 'best': Soluzione migliore trovata
        """
        preprocessing = False
        if rcpsp_max:
            try:
                self._pre_processing_rcpsp_max(n, durations, precedences, resources, consumption, horizon, release_dates, due_dates)
                preprocessing = True
            except Exception as e:
                raise e
        else:
            try:
                self._pre_processing_rcpsp(n, durations, precedences, resources, consumption, horizon)
                preprocessing = True
            except Exception as e:
                raise e

        if not preprocessing:
            raise RuntimeError("Attenzione! Devi elaborare i dati con la funzione di pre processing adatta prima di scegliere il modello.")
        
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
                all_results, best_solution, _ = self._run_sgs(
                    rcpsp_max=rcpsp_max,
                    mode="single_start",
                    rule=priority_rule,
                    top_k=top_k,
                )
                return {"type": "heuristic_single_start", "problem_difficulty": diff,
                         "results": all_results, "best": best_solution}
            elif diff == "medium":
                # In questo caso meglio il multistart soft
                all_results, best_solution, _ = self._run_sgs(
                    rcpsp_max=rcpsp_max,
                    mode="multi_start",
                    rule=None,
                    n_runs=50,
                    top_k=top_k,
                )
                return {"type": "heuristic_multi_start", "problem_difficulty": diff,
                         "results": all_results, "best": best_solution}
            else:
                # In questo caso eseguo un multistart hard
                all_results, best_solution, _ = self._run_sgs(
                    rcpsp_max=rcpsp_max,
                    mode="multi_start",
                    rule=None,
                    n_runs=500,
                    top_k=top_k,
                )
                return {"type": "heuristic_multi_start", "problem_difficulty": diff,
                         "results": all_results, "best": best_solution}
        # CASO 2
        # Soluzione esatta o normale richiesta
        else:
            # Lancio metodo esatto
            try:
                solution = self._run_exact_model(rcpsp_max=rcpsp_max)
                return {"type": "exact", "problem_difficulty": diff, "results": None, "best": solution}
            except Exception:
                all_results, best_solution, _ = self._run_sgs(rcpsp_max=rcpsp_max, mode="multi_start", rule=None, n_runs=500, top_k=top_k)
                return {"type": "heuristic_fallback", "problem_difficulty": diff, "results": all_results, "best": best_solution}

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

    def _run_sgs(self, rcpsp_max, top_k, mode = None, rule = None, n_runs = 1):
        """
        Esegue l'algoritmo euristico SGS (Serial Generation Scheme) per risolvere il problema.
        
        Delega l'esecuzione ai moduli di heuristica (multistart_rcpsp e multistart_rcpsp_max)
        che implementano lo schema decisionale dell'SGS con possibilità di:
        - Single start: Una sola esecuzione dell'algoritmo
        - Multi start: Esecuzioni multiple con regole di priorità diverse
        
        Args:
            rcpsp_max: True per RCPSP_MAX, False per RCPSP
            top_k: Numero di soluzioni top da restituire
            mode: 'single_start' o 'multi_start'
            rule: Regola di priorità da usare (opzionale)
            n_runs: Numero di iterazioni in caso di multi_start
            
        Returns:
            Tupla (all_results, best_solution, all_specs) contenente:
                - all_results: Dettagli computazionali
                - best_solution: Miglior soluzione trovata
                - all_specs: Specifiche di tutte le soluzioni
                
        Raises:
            ValueError: Se mode non è 'single_start' o 'multi_start'
        """
        if mode not in ["single_start", "multi_start"]:
            raise ValueError(f"Mode non riconosciuto: {mode}. Deve essere 'single_start' o 'multi_start'.")
        
        sgs = self._build_sgs(rcpsp_max)

        if rcpsp_max:
            config ={"time_weight": self._time_weight, "resource_weight": self._resource_weight, 
                     "priority_weight": self._priority_weight, "tardiness_weight": self._tardiness_weight, 
                     "limit_lookahead": self._limit_lookahead}
            precedences_rcpsp_max = self._precedences
            precedences_rcpsp = [(i, j) for (i, j, _, _) in precedences_rcpsp_max]
            if mode == "single_start":
                return best_solution_rcpsp_max(sgs, self._n, self._durations, precedences_rcpsp=precedences_rcpsp, precedences_rcpsp_max=precedences_rcpsp_max,
                                               resources=self._resources, consumption=self._consumption, horizon=self._horizon, **config, n_runs=1, regola=rule, top_k=top_k)
            else:  # multi_start
                return best_solution_rcpsp_max(sgs, self._n, self._durations, precedences_rcpsp=precedences_rcpsp, precedences_rcpsp_max=precedences_rcpsp_max,
                                               resources=self._resources, consumption=self._consumption, horizon=self._horizon, **config, n_runs=n_runs, regola=rule, top_k=top_k)
        else:
            if mode == "single_start":
                return best_solution_rcpsp(sgs, self._n, self._durations, self._precedences, self._resources,
                                           self._consumption, self._horizon, n_runs=1, regola=rule, top_k=top_k)
            else:  # multi_start
                return best_solution_rcpsp(sgs, self._n, self._durations, self._precedences, self._resources,
                                           self._consumption, self._horizon, n_runs=n_runs, regola=rule, top_k=top_k)

    def _build_sgs(self, rcpsp_max):
        """
        Costruisce e restituisce un'istanza dell'engine SGS appropriato.
        
        Crea l'oggetto SGS con i parametri preprocessati in modo che sia pronto
        per essere utilizzato da algoritmi euristici.
        
        Args:
            rcpsp_max: True per usare SGSEngineMax, False per usare SGSEngine
            
        Returns:
            Istanza di SGSEngine o SGSEngineMax con validazione input abilitata
        """
        if rcpsp_max:
            return SGSEngineMax(self._n, self._durations, self._precedences, self._resources,
                               self._consumption, self._horizon, self._release_dates, self._due_dates, validate_input=True)
        else:
            return SGSEngine(self._n, self._durations, self._precedences, self._resources, self._consumption, self._horizon, validate_input=True)
        
    def _run_exact_model(self, rcpsp_max):
        """
        Esegue il modello esatto (ottimale) per risolvere il problema.
        
        Costruisce un'istanza del modello esatto
        e lo risolve per ottenere la soluzione ottima.
        
        Args:
            rcpsp_max: True per risolvere RCPSP_MAX, False per RCPSP
            
        Returns:
            Soluzione ottima trovata dal modello
        """
        model = self._build_exact_model(rcpsp_max)

        return model.get_final_solution()

    def _build_exact_model(self, rcpsp_max):
        """
        Costruisce e restituisce un'istanza del modello esatto appropriato.
        
        Crea un'istanza del modello con i parametri
        preprocessati. Il modello rappresenta il problema di scheduling come problema
        di programmazione lineare intera, garantendo soluzioni ottimali.
        
        Args:
            rcpsp_max: True per usare RCPSPMaxModel, False per usare RCPSPModel
            
        Returns:
            Istanza di RCPSPModel o RCPSPMaxModel con validazione input abilitata
        """
        if rcpsp_max:
            return RCPSPMaxModel(self._n, self._durations, self._resources,
                                 self._consumption, self._precedences, self._horizon,
                                 self._release_dates, self._due_dates, validate_input=True)
        else:
            return RCPSPModel(self._n, self._durations, self._precedences, self._resources,
                              self._consumption, self._horizon, validate_input=True)

if __name__ == '__main__':
    from tests.instance_rcpsp_and_rcpsp_max import Instance

    n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, horizon, consumption, release_dates, due_dates = Instance.get_raw_instance()
    top_k = 5

    so = SolverOrchestrator()

    # so._pre_processing_rcpsp_max(n, durations, precedences_rcpsp_max, resources, consumption, horizon, release_dates, due_dates)
    soluzione = so.choose_model(n, durations, precedences_rcpsp_max, resources, consumption, horizon, release_dates, due_dates, instant_sol=False, rcpsp_max=True, top_k=top_k)
    # soluzione = so.choose_model(n, durations, precedences_rcpsp, resources, consumption, horizon, instant_sol=True, rcpsp_max=False, top_k=top_k)
    type_exact = (soluzione.get("type") == "exact")
    type_rcpsp_max = False
    if not type_exact:
        if soluzione.get("best").get("top_k_score") is not None:
            type_rcpsp_max = True
    print("=======================================================")
    print(f"Metodo utilizzato: {soluzione.get("type")}")
    print(f"Difficoltà del problema stimata: {soluzione.get("problem_difficulty")}")
    if soluzione.get("results") is not None:
        print(f"Risultati: {soluzione.get("results")}")
    if not type_exact:
        print(f"Soluzione migliore: {soluzione.get("best").get("best")}")
        if type_rcpsp_max:
            print(f"\nAltre top {top_k-1} soluzioni ordinate per score:")
            for elem in soluzione.get("best").get("top_k_score")[1:top_k]:
                print(elem)
            print(f"\nAltre top {top_k-1} soluzioni ordinate per makespan:")
            for elem in soluzione.get("best").get("top_k_makespan")[1:top_k]:
                print(elem)
        else:
            print(f"\nAltre top {top_k-1} soluzioni:")
            for elem in soluzione.get("best").get("top_k_makespan")[1:top_k]:
                print(elem)
    else:
        print(f"Soluzione migliore: {soluzione.get("best")}")
    print("=======================================================")