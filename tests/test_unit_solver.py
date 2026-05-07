import pytest
from unittest.mock import MagicMock
from solver.branch_and_bound import BranchAndBoundSolver
from solver.dataclasses.base_data_b_and_b import BaseDataBAndB
from solver.dataclasses.best_config_b_and_b import BestConfigBAndB
from pydantic import ValidationError

# --- TEST DATACLASSES ---

def test_base_data_validation():
    """Verifica che BaseDataBAndB validi correttamente i tipi di dato."""
    valid_data = {
        "n": 2,
        "durations": [0, (1, 5)],
        "precedences": [(0, 1, "FS", 0, None)],
        "resources": [10],
        "horizon": 100,
        "release_dates": [0, 0],
        "due_dates": [100, 100],
        "consumption": [[0], [2]]
    }
    data = BaseDataBAndB(**valid_data)
    assert data.n == 2
    assert isinstance(data.durations[1], tuple)

def test_base_data_invalid_types():
    """Verifica che BaseDataBAndB sollevi errore per tipi errati."""
    with pytest.raises(ValidationError):
        BaseDataBAndB(
            n="not_an_int", # Errore qui
            durations=[0, 0],
            precedences=[],
            resources=[10],
            horizon=100,
            release_dates=[],
            due_dates=[],
            consumption=[]
        )

def test_base_data_inconsistent_dimensions():
    """Verifica che BaseDataBAndB sollevi errore se le liste hanno lunghezze diverse da n."""
    base_info = {
        "n": 3,
        "durations": [0, 5, 0],
        "precedences": [],
        "resources": [10],
        "horizon": 100,
        "release_dates": [0, 0, 0],
        "due_dates": [100, 100, 100],
        "consumption": [[0]] # Errore: manca consumo per attività 1 e 2
    }
    with pytest.raises(ValidationError, match="La lunghezza di 'consumption'"):
        BaseDataBAndB(**base_info)
    
    # Test errore risorse incoerenti
    base_info["consumption"] = [[0], [0], [0]]
    base_info["resources"] = [10, 20] # 2 risorse definite, ma consumption ne ha solo 1
    with pytest.raises(ValidationError, match="ha 1 consumi, ma sono definite 2 risorse"):
        BaseDataBAndB(**base_info)

# --- TEST BRANCH AND BOUND LOGIC ---

@pytest.fixture
def mock_orch():
    return MagicMock()

@pytest.fixture
def solver(mock_orch):
    config = {
        "n": 3,
        "durations": [0, (2, 10), 0],
        "precedences": [(0, 1, "FS", 0, None), (1, 2, "FS", 0, None)],
        "resources": [(5, 10)],
        "horizon": 50,
        "release_dates": [0, 0, 0],
        "due_dates": [50, 50, 50],
        "consumption": [[0], [2], [0]],
        "top_k": 2
    }
    return BranchAndBoundSolver(mock_orch, **config)

def test_fix_to_min_max(solver):
    """Testa le funzioni di utilità per fissare i valori degli intervalli."""
    lista = [10, (5, 15), 20]
    assert solver._fix_to_min(lista) == [10, 5, 20]
    assert solver._fix_to_max(lista) == [10, 15, 20]

def test_select_best_variable_priority(solver):
    """Verifica che la selezione della variabile privilegi le attività critiche."""
    config = {
        "durations": [0, (2, 10), 0], # Attività 1 ha intervallo
        "resources": [10],
        "release_dates": [0, 0, 0],
        "due_dates": [50, 50, 50]
    }
    # Supponiamo che l'attività 1 sia critica
    critical_activities = {1}
    var = solver._select_best_variable(config, critical_activities)
    assert var == ("durations", 1)

def test_compute_lb_cpm(solver):
    """Verifica il calcolo del Lower Bound tramite CPM."""
    # Configurazione semplice: Act 0 -> Act 1 (dur 10) -> Act 2
    n = 3
    durations = [0, 10, 0]
    precedences = [(0, 1, 0, None), (1, 2, 0, None)]
    consumption = [[0], [0], [0]]
    resources = [10]
    release_dates = [0, 0, 0]
    
    lb, critical = solver._compute_lb(n, durations, precedences, consumption, resources, release_dates)
    
    # Il makespan minimo deve essere 10 (durata di Act 1)
    assert lb == 10
    assert 1 in critical

def test_compute_lb_resource(solver):
    """Verifica il calcolo del Lower Bound tramite risorse."""
    n = 2
    durations = [10, 10] # Totale lavoro 20
    precedences = []
    consumption = [[1], [1]] # Consumo totale 2
    resources = [1] # Capacità 1 -> servono almeno 20 unità di tempo
    release_dates = [0, 0]
    
    lb, _ = solver._compute_lb(n, durations, precedences, consumption, resources, release_dates)
    
    assert lb == 20

def test_extract_solution_schedule_formats(solver):
    """Testa la robustezza nell'estrazione dello schedule da diversi formati di output."""
    # Formato lista
    sol_list = {"best": {"best": {"soluzione": [{"activity": 0, "start": 0, "end": 0}]}}}
    assert solver._extract_solution_schedule(sol_list) == [{"activity": 0, "start": 0, "end": 0}]
    
    # Formato dizionario
    sol_dict = {"best": {"best": {"schedule": {0: 0, 1: 5}}}}
    assert solver._extract_solution_schedule(sol_dict) == {0: 0, 1: 5}
    
    # Caso nullo
    assert solver._extract_solution_schedule(None) is None
    assert solver._extract_solution_schedule({}) is None
