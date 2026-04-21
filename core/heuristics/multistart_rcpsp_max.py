from core.heuristics.priority_rules import wrapper_rule

def get_best_solution_overall(sgs, n, durations, precedences_rcpsp, precedences_rcpsp_max, resources, consumption, horizon, 
                              time_weight=1, resource_weight=1, priority_weight=0.5, tardiness_weight=1, limit_lookahead=5, n_runs = 100, regola: str = None):
    """
    Funzione che calcola la soluzione migliore in assoluto eseguendo n_runs volte
    le funzioni seriale e parallela per ciascuna regola di priorità.

    La soluzione migliore è data dal minore score realizzato da ogni test, calcolato
    come:
        score = makespan + 2 * penalty

    Se viene chiamata con una regola specifica, viene eseguito il multistart 
    solo per quella regola.
    """
    list_regole = ['spt', 'mts', 'grd', 'lft_rcpsp_max', 'lst_rcpsp_max', 'mslk_rcpsp_max']

    all_results = {}

    all_specs = {}

    regole_da_testare = list_regole if regola is None else [regola]

    for reg in regole_da_testare:
        if reg == 'mts':
            priority_list = wrapper_rule(reg, n=n, durations=durations, precedences_rcpsp=precedences_rcpsp, resources=resources, consumption=consumption,
                                horizon=horizon)
        else:
            priority_list = wrapper_rule(reg, n=n, durations=durations, precedences_rcpsp_max=precedences_rcpsp_max, resources=resources, consumption=consumption,
                                horizon=horizon)
            
        # Test seriale
        risultati_test, specifiche = test_multistart_stats_serial(sgs, priority_list, time_weight, resource_weight, priority_weight, tardiness_weight, limit_lookahead, n_runs)
        all_results[reg + "_serial"] = risultati_test
        all_specs[reg + "_serial"] = specifiche

        # Test parallelo
        risultati_test, specifiche = test_multistart_stats_parallel(sgs, priority_list, time_weight, resource_weight, priority_weight, tardiness_weight, limit_lookahead, n_runs)
        all_results[reg + "_parallel"] = risultati_test
        all_specs[reg + "_parallel"] = specifiche

    best_solution_overall = compute_best_solution(all_specs)

    return all_results, best_solution_overall, all_specs

def compute_best_solution(all_specs):
    
    best = None
    best_key = None
    best_score = None

    for key, specs_list in all_specs.items():
        for spec in specs_list:
            score = spec["score"]

            if best_score is None or score < best_score:
                best_score = score
                best = spec
                best_key = key

    if best is None:
        raise RuntimeError("Nessuna soluzione valida trovata.")
    
    return {
        "regola": best_key,
        "soluzione": best["solution"],
        "makespan": best["makespan"],
        "penalità": best["penalty"],
        "score": best_score
    }

def test_multistart_stats_parallel(sgs, priority_list, time_weight, resource_weight, priority_weight, tardiness_weight, limit_lookahead, n_runs=100):

    import random

    makespans = []
    solutions = []
    penalties = []
    failures = 0

    for _ in range(n_runs):

        pl = priority_list.copy()
        random.shuffle(pl)

        try:
            sol = sgs.parallel(pl, time_weight=time_weight, resource_weight=resource_weight, priority_weight=priority_weight, tardiness_weight=tardiness_weight, limit_lookahead=limit_lookahead)
            makespan = max(x["end"] for x in sol)
            makespans.append(makespan)
            solutions.append(sol)
            penalties.append(sgs.penalty_par)
        except RuntimeError:
            failures += 1

    if not makespans:
        raise RuntimeError("Nessuna soluzione trovata!")
    
    specifiche = []

    for i in range(len(makespans)):
        specifiche.append({"makespan": makespans[i], "solution": solutions[i], "penalty": penalties[i], "score": makespans[i] + (2 * penalties[i])})

    risultati = {"runs": n_runs, "makespans": makespans, "success": len(makespans), "failures": failures, 
                 "best": min(makespans), "average": sum(makespans)/len(makespans), "worst": max(makespans)}

    return risultati, specifiche

def test_multistart_stats_serial(sgs, priority_list, time_weight, resource_weight, priority_weight, tardiness_weight, limit_lookahead, n_runs=100):

    import random

    makespans = []
    solutions = []
    penalties = []
    failures = 0

    for _ in range(n_runs):

        pl = priority_list.copy()
        random.shuffle(pl)

        try:
            sol = sgs.serial(pl, time_weight=time_weight, resource_weight=resource_weight, priority_weight=priority_weight, tardiness_weight=tardiness_weight, limit_lookahead=limit_lookahead)
            makespan = max(x["end"] for x in sol)
            makespans.append(makespan)
            solutions.append(sol)
            penalties.append(sgs.penalty_ser)
        except RuntimeError:
            failures += 1

    if not makespans:
        raise RuntimeError("Nessuna soluzione trovata!")

    specifiche = []

    for i in range(len(makespans)):
        specifiche.append({"makespan": makespans[i], "solution": solutions[i], "penalty": penalties[i], "score": makespans[i] + (2 * penalties[i])})

    risultati = {"runs": n_runs, "makespans": makespans, "success": len(makespans), "failures": failures, 
                 "best": min(makespans), "average": sum(makespans)/len(makespans), "worst": max(makespans)}

    return risultati, specifiche