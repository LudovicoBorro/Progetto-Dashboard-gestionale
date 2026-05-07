"""
test_unit_orchestrator.py
------------------
Modulo per testare il modulo orchestrator.py, che si occupa di orchestrare 
l'esecuzione dei modelli di ottimizzazione.
"""
from tests.instance_rcpsp_and_rcpsp_max import Instance
from solver.orchestrator import SolverOrchestrator
from solver.preprocessing import _pre_processing_rcpsp_max
from core.heuristics.sgs_engine_rcpsp_max import SGSEngine
from core.heuristics.priority_rules import wrapper_rule

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
    # 'best' è il contenitore, 'best.best' è la soluzione singola migliore
    best_sol = soluzione["best"]["best"]
    assert "makespan" in best_sol
    assert best_sol["makespan"] > 0

def _check_schedule(soluzione, n):
    best_sol = soluzione["best"]["best"]
    # Pydantic dump usa il nome del campo 'soluzione'
    schedule = best_sol.get("soluzione") or best_sol.get("schedule")
    
    assert isinstance(schedule, list)
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

def _check_solutions(best_container, top_k):
    # best_container è soluzione["best"]
    assert best_container.get("best") is not None

    if best_container.get("top_k_makespan") is not None:
            assert len(best_container["top_k_makespan"]) <= top_k

    if best_container.get("top_k_score") is not None:
        assert len(best_container["top_k_score"]) <= top_k

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


def _check_schedule_precedences(schedule, precedences):
    start_times = {item["activity"]: item["start"] for item in schedule}
    for (i, j, min_lag, max_lag) in precedences:
        assert start_times[j] >= start_times[i] + min_lag
        if max_lag is not None:
            assert start_times[j] <= start_times[i] + max_lag


def test_sgs_engine_serial_and_parallel_end_dummy_schedule():
    n = 5
    durations = [3, 2, 4, 3, 2]
    resources = [10, 10, 10]
    consumption = [
        [0, 0, 0],
        [2, 1, 1],
        [1, 1, 1],
        [2, 1, 1],
        [1, 1, 1],
    ]
    precedences_rcpsp_max = [
        (0, 1, "FS", 0, None),
        (1, 2, "FS", 0, None),
        (2, 3, "FS", 0, None),
        (3, 4, "FS", 0, None),
    ]
    horizon = 20
    release_dates = [None] * n
    due_dates = [None] * n

    processed = _pre_processing_rcpsp_max(
        n=n,
        durations=durations,
        precedences=precedences_rcpsp_max,
        resources=resources,
        consumption=consumption,
        horizon=horizon,
        release_dates=release_dates,
        due_dates=due_dates,
    )

    sgs = SGSEngine(
        processed.n,
        processed.durations,
        processed.precedences,
        processed.resources,
        processed.consumption,
        processed.horizon,
        release_dates=processed.release_dates,
        due_dates=processed.due_dates,
        validate_input=True,
    )

    priority_list = wrapper_rule(
        "spt",
        n=processed.n,
        durations=processed.durations,
        precedences_rcpsp_max=processed.precedences,
        resources=processed.resources,
        consumption=processed.consumption,
        horizon=processed.horizon,
    )

    schedule_serial = sgs.serial(
        priority_list,
        time_weight=1,
        resource_weight=1,
        priority_weight=1,
        tardiness_weight=1,
        limit_lookahead=5,
    )
    assert isinstance(schedule_serial, list)
    assert len(schedule_serial) == processed.n
    _check_schedule_precedences(schedule_serial, processed.precedences)

    schedule_parallel = sgs.parallel(
        priority_list,
        time_weight=1,
        resource_weight=1,
        priority_weight=1,
        tardiness_weight=1,
        limit_lookahead=5,
    )
    assert isinstance(schedule_parallel, list)
    assert len(schedule_parallel) == processed.n
    _check_schedule_precedences(schedule_parallel, processed.precedences)
