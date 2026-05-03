from core.heuristics.priority_rules import wrapper_rule

def get_best_solution_overall(sgs, n, durations, precedences_rcpsp, precedences_rcpsp_max, resources, consumption, horizon, n_runs, config=None):
    """
    Funzione che calcola la soluzione migliore in assoluto eseguendo n_runs volte
    le funzioni seriale e parallela per ciascuna regola di priorità.

    La soluzione migliore è data dal minore score realizzato da ogni test, calcolato
    come:
        score = makespan + 2 * penalty

    Se viene chiamata con una regola specifica, viene eseguito il multistart 
    solo per quella regola.
    """
    if config is None:
        config = {}
    
    top_k = config.get('top_k', 5)
    time_weight = config.get('time_weight', 1)
    resource_weight = config.get('resource_weight', 1)
    priority_weight = config.get('priority_weight', 0.5)
    tardiness_weight = config.get('tardiness_weight', 1)
    limit_lookahead = config.get('limit_lookahead', 5)
    regola = config.get('regola', None)
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

    best_solution_overall = compute_best_solution(all_specs, min(top_k, len(all_specs.get(regole_da_testare[0]+"_parallel"))))

    return all_results, best_solution_overall, all_specs

def compute_best_solution(all_specs, top_k):
    
    all_candidates = []

    # 1) Flatten di tutte le soluzioni
    for key, specs_list in all_specs.items():
        for spec in specs_list:
            all_candidates.append({
                "regola": key,
                "soluzione": spec["solution"],
                "makespan": spec["makespan"],
                "penalità": float(spec["penalty"]),
                "score": float(spec["score"])
            })

    all_candidates = unique_solutions(all_candidates)

    if not all_candidates:
        raise RuntimeError("Nessuna soluzione valida trovata.")

    # 2) Ordinamento per score
    sorted_by_score = sorted(all_candidates, key=lambda x: x["score"])

    # 3) Ordinamento per makespan
    sorted_by_makespan = sorted(all_candidates, key=lambda x: x["makespan"])

    # 4) Best assoluto, secondo lo score
    best = sorted_by_score[0]

    return {
        "best": best,
        "top_k_score": sorted_by_score[:top_k],
        "top_k_makespan": sorted_by_makespan[:top_k]
    }

def unique_solutions(candidates):
    seen = set()
    unique = []

    for c in candidates:
        key = tuple((x["activity"], x["start"], x["end"]) for x in c["soluzione"])
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique

def test_multistart_stats_parallel(sgs, priority_list, time_weight, resource_weight, priority_weight, tardiness_weight, limit_lookahead, n_runs=100):

    import random

    makespans = []
    solutions = []
    penalties = []
    failures = 0

    for _ in range(n_runs):

        pl = priority_list.copy()
        if n_runs > 1:
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
        if n_runs > 1:
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