"""
test_unit_rcpsp.py
------------------
Modulo per testare il modello rcpsp.py utilizzano dataset della libreria 
PSPLIB.
"""
from utils.getters.get_psplib_instance import get_psplib_instance
from core.exact.rcpsp import Model
from core.exact.utils import solve
from psplib import parse
import time
    
def build_model(dataset):

    activities, numero_act, durations, precedences, resources, consumption, horizon = get_psplib_instance(dataset)

    model = Model(n=numero_act, 
                        durations=durations, 
                        precedences=precedences,
                        resources=resources,
                        consumption=consumption,
                        horizon=horizon,
                        validate_input=True
                        )
    
    print("Modello correttamente creato!")
    print("Attività totali:", numero_act)
    print("Successori esempio:", activities[0].successors)
    print("Max successor:", max(s for a in activities for s in a.successors))
    print("Numero precedenze:", len(precedences))
    print("Esempio precedenze:", precedences[:10])

    return model
            
def solve_model(model):
    start_time = time.time()
    status = solve(model, time_limit=10, verbose=False)
    end_time = time.time()

    print("="*60)
    print(f"Il problema ha avuto esito: {status}")
    print(f"\nSoluzione trovata: {model.makespan} giorni")
    print("-"*60)
    print(f"Il solver ha impiegato {end_time-start_time:.6f} secondi")
    print("-"*60)
    if status == "OPTIMAL" or status == "FEASIBLE":
        print(model.get_schedule())
    print("="*60)

    return status

def validate_solution(model, status) -> bool:
    """
    Valida la soluzione trovata dal solver verificando tutti i vincoli
    del modello RCPSP classico:

        1. Soluzione disponibile
        2. Tutte le attività hanno un tempo di inizio
        3. Attività fittizia iniziale a t=0
        4. Makespan == start[n-1]
        5. Start non negativi e completamento entro deadline
        6. Vincoli di precedenza finish-to-start
        7. Vincoli di risorsa (nessuna violazione di capacità)
    """

    inst = model
    n = inst._n
    durations = inst._durations
    start = inst._start_times
    prec = inst._precedences
    resources = inst._resources
    consump = inst._consumption
    deadline = inst._horizon

    if status not in ("OPTIMAL", "FEASIBLE"):
        print(f"⚠️  Nessuna soluzione da validare (status={status})")
        return False

    if start is None:
        _report(["start_times è None nonostante lo status sia risolutivo."])
        return False

    errors: list[str] = []
    _validate_basic_solution(n, start, durations, deadline, inst, errors)
    _validate_precedences(prec, start, durations, errors)
    _validate_resource_constraints(resources, consump, start, durations, errors)

    _report(errors)
    return len(errors) == 0


def _validate_basic_solution(
    n: int,
    start: dict[int, int],
    durations: list[int],
    deadline: int,
    inst,
    errors: list[str],
) -> None:
    missing = [i for i in range(n) if i not in start]
    if missing:
        errors.append(f"Attività senza start time: {missing}")

    if start.get(0, -1) != 0:
        errors.append(
            f"L'attività fittizia 0 deve iniziare a t=0, "
            f"trovato start[0]={start.get(0)}."
        )

    if inst.makespan != start.get(n - 1):
        errors.append(
            f"makespan={inst.makespan} != start[{n-1}]={start.get(n - 1)}."
        )

    for i in range(n):
        s = start.get(i)
        if s is None:
            continue
        if s < 0:
            errors.append(f"Attività {i}: start={s} negativo.")
        end_i = s + durations[i]
        if end_i > deadline:
            errors.append(
                f"Attività {i}: end={end_i} supera deadline={deadline} "
                f"(start={s}, duration={durations[i]})."
            )


def _validate_precedences(
    prec: list[tuple[int, int]],
    start: dict[int, int],
    durations: list[int],
    errors: list[str],
) -> None:
    for idx, (i, j) in enumerate(prec):
        si = start.get(i)
        sj = start.get(j)
        if si is None or sj is None:
            continue

        min_required = si + durations[i]
        if sj < min_required:
            errors.append(
                f"Precedenza [{idx}] ({i}→{j}): "
                f"start[{j}]={sj} < start[{i}]+dur[{i}] = {min_required}. "
                f"Attività {j} inizia prima che {i} sia completata."
            )


def _validate_resource_constraints(
    resources: list[int],
    consump: list[list[int]],
    start: dict[int, int],
    durations: list[int],
    errors: list[str],
) -> None:
    for k in range(len(resources)):
        delta: dict[int, int] = {}

        for i in range(len(durations)):
            s = start.get(i)
            if s is None or durations[i] == 0:
                continue
            c = consump[i][k]
            if c == 0:
                continue
            delta[s] = delta.get(s, 0) + c
            delta[s + durations[i]] = delta.get(s + durations[i], 0) - c

        current = 0
        for t in sorted(delta):
            current += delta[t]
            if current > resources[k]:
                errors.append(
                    f"Risorsa {k}: utilizzo={current} > capacità={resources[k]} "
                    f"a partire da t={t}."
                )

import pytest
from tests.config import DATASETS

@pytest.mark.parametrize("dataset", DATASETS)
def test_rcpsp_solution(dataset):
    model = build_model(dataset)
    status = solve_model(model)

    assert status != "ERROR"

    if status == "INFEASIBLE":
        pytest.skip("Istanza infeasible")

    assert status in ("OPTIMAL", "FEASIBLE")
    assert validate_solution(model, status)
    
# ──────────────────────────────────────────────────────────────────────────────
# Report errors
# ──────────────────────────────────────────────────────────────────────────────

def _report(errors: list[str]) -> None:
    print("=" * 60)
    print("VALIDAZIONE SOLUZIONE")
    print("=" * 60)
    if not errors:
        print("✅  Soluzione valida: tutti i vincoli rispettati.")
    else:
        print(f"❌  {len(errors)} errore/i rilevato/i:")
        for e in errors:
            print(f"    • {e}")
    print("=" * 60)