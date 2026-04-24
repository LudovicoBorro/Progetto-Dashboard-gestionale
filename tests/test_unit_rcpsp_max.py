"""
test_unit_rcpsp_max.py
------------------
Modulo per testare il modello rcpsp_max.py utilizzano dataset della libreria 
PSPLIB.
"""
from utils.getters.get_psplib_instance import get_psplib_instance
from core.exact.rcpsp_max import Model
from core.exact.utils import solve
from psplib import parse
import time, random

def build_model(dataset):

    _, numero_act, durations, precedences, resources, consumption, horizon, release_dates, due_dates = get_psplib_instance(dataset, rcpsp_max=True)

    return Model(
        n=numero_act,
        durations=durations,
        precedences=precedences,
        resources=resources,
        consumption=consumption,
        horizon=horizon,
        release_dates=release_dates,
        due_dates=due_dates,
        validate_input=True,
    )

def solve_model(model):
    start_time = time.time()
    status = solve(model, time_limit=10, verbose=False)
    end_time = time.time()

    if status == "INFEASIBLE":
        print("⚠️ Istanza infeasible — probabilmente lag/due troppo stretti")

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

def _validate_status(status, start, errors) -> bool:
    if status not in ("OPTIMAL", "FEASIBLE"):
        print(f"⚠️  Nessuna soluzione da validare (status={status})")
        return False

    if start is None:
        errors.append("start_times è None nonostante lo status sia risolutivo.")
        _report(errors, [])
        return False

    return True


def _validate_task_start_times(n, start, errors) -> None:
    missing = [i for i in range(n) if i not in start]
    if missing:
        errors.append(f"Attività senza start time: {missing}")

    if start.get(0, -1) != 0:
        errors.append(
            f"L'attività fittizia 0 deve iniziare a t=0, "
            f"trovato start[0]={start.get(0)}."
        )


def _validate_makespan(inst, n, start, errors) -> None:
    expected_makespan = start.get(n - 1)
    if inst.makespan != expected_makespan:
        errors.append(
            f"makespan={inst.makespan} != start[{n-1}]={expected_makespan}."
        )


def _validate_durations_and_horizon(n, durations, start, horizon, errors) -> None:
    for i in range(n):
        s = start.get(i)
        if s is None:
            continue
        if s < 0:
            errors.append(f"Attività {i}: start={s} negativo.")
        end_i = s + durations[i]
        if end_i > horizon:
            errors.append(
                f"Attività {i}: end={end_i} supera horizon={horizon}."
            )


def _validate_precedences(prec, start, errors) -> None:
    for idx, (i, j, min_lag, max_lag) in enumerate(prec):
        si = start.get(i)
        sj = start.get(j)
        if si is None or sj is None:
            continue

        diff = sj - si

        if diff < min_lag:
            errors.append(
                f"Precedenza [{idx}] ({i}→{j}): "
                f"start[{j}]-start[{i}] = {diff} < min_lag={min_lag}. "
                f"(start[{i}]={si}, start[{j}]={sj})"
            )

        if max_lag is not None and diff > max_lag:
            errors.append(
                f"Precedenza [{idx}] ({i}→{j}): "
                f"start[{j}]-start[{i}] = {diff} > max_lag={max_lag}. "
                f"(start[{i}]={si}, start[{j}]={sj})"
            )


def _validate_release_dates(n, start, rd, errors) -> None:
    if rd is None:
        return

    for i in range(n):
        if rd[i] is None:
            continue
        s = start.get(i)
        if s is None:
            continue

        if s < rd[i]:
            errors.append(
                f"Attività {i}: start={s} < release_date={rd[i]}."
            )


def _validate_due_dates(n, durations, start, dd, errors) -> None:
    if dd is None:
        return

    for i in range(n):
        if dd[i] is None:
            continue
        s = start.get(i)
        if s is None:
            continue

        end_i = s + durations[i]
        if end_i > dd[i]:
            errors.append(
                f"Attività {i}: end={end_i} > due_date={dd[i]} "
                f"(start={s}, duration={durations[i]})."
            )


def _validate_release_due_dates(n, durations, start, rd, dd, errors) -> None:
    _validate_release_dates(n, start, rd, errors)
    _validate_due_dates(n, durations, start, dd, errors)


def _validate_resource_usage(n, start, consump, durations, resources, errors) -> None:
    num_resources = len(resources)

    for k in range(num_resources):
        usage_events: dict[int, int] = {}

        for i in range(n):
            s = start.get(i)
            if s is None or durations[i] == 0:
                continue
            c = consump[i][k]
            if c == 0:
                continue

            usage_events[s] = usage_events.get(s, 0) + c
            usage_events[s + durations[i]] = usage_events.get(
                s + durations[i], 0
            ) - c

        current = 0
        for t in sorted(usage_events):
            current += usage_events[t]
            if current > resources[k]:
                errors.append(
                    f"Risorsa {k}: utilizzo={current} > capacità={resources[k]} "
                    f"a t={t}."
                )


def validate_solution(model, status) -> bool:
    """
    Valida la soluzione trovata dal solver verificando tutti i vincoli
    del modello RCPSP/Max:

        1. Soluzione disponibile
        2. Attività fittizia iniziale a t=0
        3. Makespan == start[n-1]
        4. Durate e completamento non negativi
        5. Vincoli di precedenza generalizzati (min_lag e max_lag)
        6. Release dates
        7. Due dates
        8. Vincoli di risorsa (nessuna sovrapposizione oltre capacità)
    """

    inst = model
    n = inst._n
    durations = inst._durations
    start = inst._start_times
    prec = inst._precedences
    resources = inst._resources
    consump = inst._consumption
    rd = inst._release_dates
    dd = inst._due_dates
    horizon = inst._horizon

    errors = []
    warnings = []

    if not _validate_status(status, start, errors):
        return False

    _validate_task_start_times(n, start, errors)
    _validate_makespan(inst, n, start, errors)
    _validate_durations_and_horizon(n, durations, start, horizon, errors)
    _validate_precedences(prec, start, errors)
    _validate_release_due_dates(n, durations, start, rd, dd, errors)
    _validate_resource_usage(n, start, consump, durations, resources, errors)

    _report(errors, warnings)
    return len(errors) == 0

import pytest
from tests.config import DATASETS

@pytest.mark.parametrize("dataset", DATASETS)
def test_rcpsp_max_solution(dataset):
    random.seed(42)

    model = build_model(dataset=dataset)
    status = solve_model(model)

    assert status != "ERROR"

    if status == "INFEASIBLE":
        pytest.skip("Istanza infeasible")

    assert status in ("OPTIMAL", "FEASIBLE")
    assert validate_solution(model, status)

# ──────────────────────────────────────────────────────────────────────────────
# Report errors
# ──────────────────────────────────────────────────────────────────────────────

def _report(errors: list[str], warnings: list[str]) -> None:
    print("=" * 60)
    print("VALIDAZIONE SOLUZIONE")
    print("=" * 60)
    if not errors and not warnings:
        print("✅  Soluzione valida: tutti i vincoli rispettati.")
    else:
        if warnings:
            print(f"⚠️  {len(warnings)} warning(s):")
            for w in warnings:
                print(f"    • {w}")
        if errors:
            print(f"❌  {len(errors)} errore/i rilevato/i:")
            for e in errors:
                print(f"    • {e}")
    print("=" * 60)
