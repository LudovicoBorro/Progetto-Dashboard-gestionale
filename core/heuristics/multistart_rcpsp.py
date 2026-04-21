from core.heuristics.priority_rules import wrapper_rule

def get_best_solution_overall(sgs, n, durations, precedences, resources, consumption, horizon, n_runs = 100, regola: str = None):
    """
    Funzione che calcola la soluzione migliore in assoluto eseguendo n_runs volte
    le funzioni seriale e parallela per ciascuna regola di priorità.

    La soluzione migliore è data dal minore makespan in assoluto.

    Se viene chiamata con una regola specifica, viene eseguito il multistart 
    solo per quella regola.
    """
    list_regole = ['spt', 'mts', 'grd', 'lft_rcpsp', 'lst_rcpsp', 'mslk_rcpsp']

    best_solutions = {}

    all_results = {}

    regole_da_testare = list_regole if regola is None else [regola]

    for reg in regole_da_testare:
        
        priority_list = wrapper_rule(reg, n, durations, precedences, resources=resources, consumption=consumption,
                                horizon=horizon)

        # Test seriale
        risultati_test, best_sol = test_multistart_stats_serial(sgs, priority_list, n_runs)
        best_solutions[reg + "_serial"] = best_sol
        all_results[reg + "_serial"] = risultati_test

        # Test parallelo
        risultati_test, best_sol = test_multistart_stats_parallel(sgs, priority_list, n_runs)
        best_solutions[reg + "_parallel"] = best_sol
        all_results[reg + "_parallel"] = risultati_test

    best_solution_overall = get_best_solution(best_solutions)

    return all_results, best_solution_overall

def get_best_solution(best_solutions):

    best = None
    regola = None
    min_makespan = None

    for reg, sol in best_solutions.items():
        if min_makespan is None or sol.get("makespan") < min_makespan:
            min_makespan = sol.get("makespan")
            best = sol
            regola = reg
    
    if best is None:
        raise RuntimeError("Nessuna soluzione valida trovata.")
    
    return {"regola": regola, "soluzione": best, "makespan": min_makespan}

def test_multistart_stats_parallel(sgs, priority_list, n_runs=100):

    import random

    makespans = []
    best_solution = None
    best_makespan = None
    best = {}
    failures = 0

    for _ in range(n_runs):

        pl = priority_list.copy()
        random.shuffle(pl)

        try:
            sol = sgs.parallel(pl)
            makespan = max(x["end"] for x in sol)
            makespans.append(makespan)
            if best_makespan is None or makespan < best_makespan:
                best_makespan = makespan
                best_solution = sol
        except RuntimeError:
            failures += 1
    
    if not makespans:
        raise RuntimeError("Nessuna soluzione trovata!")

    best = {"makespan": best_makespan, "solution": best_solution}

    risultati = {"runs": n_runs, "makespans": makespans, "success": len(makespans), "failures": failures, 
                 "best": min(makespans), "average": sum(makespans)/len(makespans), "worst": max(makespans)}

    return risultati, best

def test_multistart_stats_serial(sgs, priority_list, n_runs=100):

    import random

    makespans = []
    best_solution = None
    best_makespan = None
    best = {}
    failures = 0

    for _ in range(n_runs):

        pl = priority_list.copy()
        random.shuffle(pl)

        try:
            sol = sgs.serial(pl)
            makespan = max(x["end"] for x in sol)
            makespans.append(makespan)
            if best_makespan is None or makespan < best_makespan:
                best_makespan = makespan
                best_solution = sol
        except RuntimeError:
            failures += 1

    if not makespans:
        raise RuntimeError("Nessuna soluzione trovata!")

    best = {"makespan": best_makespan, "solution": best_solution}

    risultati = {"runs": n_runs, "makespans": makespans, "success": len(makespans), "failures": failures, 
                 "best": min(makespans), "average": sum(makespans)/len(makespans), "worst": max(makespans)}

    return risultati, best