from core.heuristics.multistart_rcpsp import get_best_solution_overall as best_solution_rcpsp
from core.heuristics.multistart_rcpsp_max import get_best_solution_overall as best_solution_rcpsp_max
from core.exact.rcpsp import Model as RCPSPModel
from core.exact.rcpsp_max import Model as RCPSPMaxModel
from core.heuristics.sgs_engine_rcpsp_max import SGSEngine as SGSEngineMax
from core.heuristics.sgs_engine_rcpsp import SGSEngine

def _run_sgs(orch, rcpsp_max, top_k, mode = None, rule = None, n_runs = 1):
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
    
    sgs = _build_sgs(orch, rcpsp_max)

    if rcpsp_max:
        config ={"time_weight": orch._time_weight, "resource_weight": orch._resource_weight, 
                    "priority_weight": orch._priority_weight, "tardiness_weight": orch._tardiness_weight, 
                    "limit_lookahead": orch._limit_lookahead, "regola": rule, "top_k": top_k}
        precedences_rcpsp_max = orch._precedences
        precedences_rcpsp = [(i, j) for (i, j, _, _) in precedences_rcpsp_max]
        if mode == "single_start":
            return best_solution_rcpsp_max(sgs, orch._n, orch._durations, precedences_rcpsp=precedences_rcpsp, precedences_rcpsp_max=precedences_rcpsp_max,
                                            resources=orch._resources, consumption=orch._consumption, horizon=orch._horizon, config=config, n_runs=1)
        else:  # multi_start
            return best_solution_rcpsp_max(sgs, orch._n, orch._durations, precedences_rcpsp=precedences_rcpsp, precedences_rcpsp_max=precedences_rcpsp_max,
                                            resources=orch._resources, consumption=orch._consumption, horizon=orch._horizon, config=config, n_runs=n_runs)
    else:
        if mode == "single_start":
            return best_solution_rcpsp(sgs, orch._n, orch._durations, orch._precedences, orch._resources,
                                        orch._consumption, orch._horizon, n_runs=1, regola=rule, top_k=top_k)
        else:  # multi_start
            return best_solution_rcpsp(sgs, orch._n, orch._durations, orch._precedences, orch._resources,
                                        orch._consumption, orch._horizon, n_runs=n_runs, regola=rule, top_k=top_k)

def _build_sgs(orch, rcpsp_max):
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
        return SGSEngineMax(orch._n, orch._durations, orch._precedences, orch._resources,
                            orch._consumption, orch._horizon, orch._release_dates, orch._due_dates, validate_input=True)
    else:
        return SGSEngine(orch._n, orch._durations, orch._precedences, orch._resources, orch._consumption, orch._horizon, validate_input=True)
    
def _run_exact_model(orch, rcpsp_max):
    """
    Esegue il modello esatto (ottimale) per risolvere il problema.
    
    Costruisce un'istanza del modello esatto
    e lo risolve per ottenere la soluzione ottima.
    
    Args:
        rcpsp_max: True per risolvere RCPSP_MAX, False per RCPSP
        
    Returns:
        Soluzione ottima trovata dal modello
    """
    model = _build_exact_model(orch, rcpsp_max)

    return model.get_final_solution()

def _build_exact_model(orch, rcpsp_max):
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
        return RCPSPMaxModel(orch._n, orch._durations, orch._resources,
                                orch._consumption, orch._precedences, orch._horizon,
                                orch._release_dates, orch._due_dates, validate_input=True)
    else:
        return RCPSPModel(orch._n, orch._durations, orch._precedences, orch._resources,
                            orch._consumption, orch._horizon, validate_input=True)