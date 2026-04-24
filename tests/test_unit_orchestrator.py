"""
test_unit_orchestrator.py
------------------
Modulo per testare il modulo orchestrator.py, che si occupa di orchestrare 
l'esecuzione dei modelli di ottimizzazione.
"""
from tests.instance_rcpsp_and_rcpsp_max import Instance
from solver.orchestrator import SolverOrchestrator

def test_orchestrator_exact():
    """
    Testa la funzione choose_model del modulo orchestrator.py, verificando che
    vengano restituite soluzioni coerenti con le istanze di input.

    In particolare, testa che il metodo esatto venga correttamente chiamato e
    che la soluzione restituita abbia una struttura coerente, con un makespan positivo
    e un schedule valido (se presente).
    """

    so = SolverOrchestrator()

    (n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, 
     horizon, consumption, release_dates, due_dates) = Instance.get_raw_instance()
    top_k = 5

    # RCPSP

    soluzione = so.choose_model(n, durations, precedences_rcpsp, 
                                resources, consumption, horizon, release_dates, due_dates, instant_sol=False, rcpsp_max=False, top_k=top_k)
    
    _check_exact(soluzione, n)

    # RCPSP_MAX

    soluzione = so.choose_model(n, durations, precedences_rcpsp_max, 
                                resources, consumption, horizon, release_dates, due_dates, instant_sol=False, rcpsp_max=True, top_k=top_k)
    
    _check_exact(soluzione, n)

def test_orchestrator_heuristic():
    """
    Testa la funzione choose_model del modulo orchestrator.py, verificando che
    vengano restituite soluzioni coerenti con le istanze di input.
    
    In particolare, testa che il metodo euristico venga correttamente chiamato e
    che la soluzione restituita abbia una struttura coerente, con un makespan positivo
    e un schedule valido (se presente).
    """
    so = SolverOrchestrator()

    (n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, 
     horizon, consumption, release_dates, due_dates) = Instance.get_raw_instance()
    top_k = 5

    # RCPSP

    soluzione = so.choose_model(n, durations, precedences_rcpsp, 
                                resources, consumption, horizon, release_dates, due_dates, instant_sol=True, rcpsp_max=False, top_k=top_k)
    
    _check_heuristic(soluzione, top_k)

    # RCPSP_MAX

    soluzione = so.choose_model(n, durations, precedences_rcpsp_max, 
                            resources, consumption, horizon, release_dates, due_dates, instant_sol=True, rcpsp_max=True, top_k=top_k)

    _check_heuristic(soluzione, top_k)

def _check_struttura(soluzione):
    assert soluzione is not None
    assert "type" in soluzione
    assert "best" in soluzione
    assert "problem_difficulty" in soluzione

def _check_tipo(soluzione, expected_types):
    assert soluzione["type"] in expected_types
    assert soluzione["problem_difficulty"] in ("easy", "medium", "hard")

def _check_makespan(soluzione):
    best = soluzione["best"]
    assert "makespan" in best
    assert best["makespan"] > 0

def _check_schedule(soluzione, n):
    best = soluzione["best"]
    schedule = best.get("schedule")
    assert isinstance(schedule, list)
    if "schedule" in best:
        schedule = best["schedule"]

    assert len(schedule) == n + 2

    for dizio in schedule:
        assert dizio.get("activity") >= 0
        assert dizio.get("start") >= 0
        assert dizio.get("end") >= 0
        assert dizio.get("duration") >= 0
        assert dizio.get("end") == dizio.get("start") + dizio.get("duration")

def _check_multistart(soluzione, tipo, diff):
    if tipo == "heuristic_multi_start":
        results = soluzione["results"]
        assert results is not None
        assert isinstance(results, dict)
        assert len(results) > 1

        for value in results.values():
            runs = value.get("runs")
            assert runs is not None
            assert runs > 1

            assert value.get("success") + int(value.get("failures")) == runs

def _check_solutions(best, top_k):

    if "best" in best:
        best_sol = best["best"]
    else:
        best_sol = best

    assert best_sol is not None

    if best.get("top_k_makespan") is not None:
            assert len(best["top_k_makespan"]) <= top_k

    if best.get("best").get("top_k_score") is not None:
        assert len(best["top_k_score"]) <= top_k

def _check_exact(soluzione, n):

    # --- struttura ---
    _check_struttura(soluzione)

    # --- tipo ---
    _check_tipo(soluzione, expected_types=["exact", "heuristic_fallback"])

    # --- makespan ---
    _check_makespan(soluzione)

    # --- schedule ---
    _check_schedule(soluzione, n)

def _check_heuristic(soluzione, top_k):

    # --- struttura ---
    _check_struttura(soluzione)

    # --- tipo ---
    _check_tipo(soluzione, expected_types=["heuristic_single_start", "heuristic_multi_start"])

    best = soluzione["best"]
    diff = soluzione["problem_difficulty"]
    tipo = soluzione["type"]

    # --- solutions ---
    _check_solutions(best, top_k)

    # --- multistart ---
    _check_multistart(soluzione, tipo, diff)

    # --- logica ---
    if tipo.startswith("heuristic"):
        if diff == "easy":
            assert tipo == "heuristic_single_start"
        elif diff in ("medium", "hard"):
            assert tipo == "heuristic_multi_start"