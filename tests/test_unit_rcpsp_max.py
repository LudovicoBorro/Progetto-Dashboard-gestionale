"""
test_unit_rcpsp_max.py
------------------
Modulo per testare il modello rcpsp_max.py utilizzano dataset della libreria 
PSPLIB.
"""
from core.exact.rcpsp_max import Model
from psplib import parse
import time, random

class Test:

    def __init__(self, dataset: str):
        self._instance = parse(dataset, instance_format="psplib")
        self._inst = None
        self._model = None
        self._status = None

    def build_model(self):
        
        numero_act = self._instance.num_activities
        durations = []
        consumption = []
        resources = []
        precedences = []
        horizon = int(2.0 * sum(a.modes[0].duration for a in self._instance.activities))
        release_dates = []
        due_dates = []

        # Fill dei dati secondo il formato psplib
        for i,a in enumerate(self._instance.activities):
            durations.append(a.modes[0].duration)
            consumption.append(a.modes[0].demands)

            if i == 0:
                release_dates.append(0)
                due_dates.append(None)
            elif i == numero_act - 1:
                release_dates.append(None)
                due_dates.append(None)
            else:
                # RELEASE
                if random.random() < 0.4:
                    release_dates.append(random.randint(0, int(0.3 * horizon)))
                else:
                    release_dates.append(None)

                # DUE
                if random.random() < 0.5:
                    base = random.randint(int(0.3 * horizon), int(0.7 * horizon))
                    slack = random.randint(0, 2 * a.modes[0].duration)
                    due_dates.append(base + slack)
                else:
                    due_dates.append(None)

            for succ in a.successors:
                min_lag = random.randint(0, max(1, a.modes[0].duration // 3))
                # max_lag = min_lag + random.randint(0, a.modes[0].duration)
                # max_lag = horizon
                max_lag = None
                precedences.append((i, succ, min_lag, max_lag))

        for r in self._instance.resources:
            resources.append(r.capacity)

        self._inst = Model(n=numero_act, 
                            durations=durations, 
                            precedences=precedences,
                            resources=resources,
                            consumption=consumption,
                            horizon=horizon,
                            release_dates=release_dates,
                            due_dates=due_dates,
                            validate_input=True
                            )
        
        print("Modello correttamente creato!")
        print("Attività totali:", numero_act)
        print("Successori esempio:", self._instance.activities[0].successors)
        print("Max successor:", max(s for a in self._instance.activities for s in a.successors))
        print("Numero precedenze:", len(precedences))
        print("Esempio precedenze:", precedences[:10])

    def solve_model(self):
        start_time = time.time()
        self._status = self._inst.solve(time_limit=300, verbose=False)
        end_time = time.time()

        if self._status == "INFEASIBLE":
            print("⚠️ Istanza infeasible — probabilmente lag/due troppo stretti")

        print(f"="*60)
        print(f"Il problema ha avuto esito: {self._status}")
        print(f"\nSoluzione trovata: {self._inst.makespan} giorni")
        print(f"-"*60)
        print(f"Il solver ha impiegato {end_time-start_time:.6f} secondi")
        print(f"-"*60)
        if self._status == "OPTIMAL" or self._status == "FEASIBLE":
            print(self._inst.get_schedule())
        print(f"="*60)

    def validate_solution(self) -> bool:
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

        # ── Recupero strutture ────────────────────────────────────────────────────

        inst      = self._inst
        n         = inst._n
        durations = inst._durations
        start     = inst._start_times
        prec      = inst._precedences
        resources = inst._resources
        consump   = inst._consumption
        rd        = inst._release_dates
        dd        = inst._due_dates
        horizon   = inst._horizon

        errors   = []
        warnings = []

        # ── 0. Soluzione disponibile ──────────────────────────────────────────────

        if self._status not in ("OPTIMAL", "FEASIBLE"):
            print(f"⚠️  Nessuna soluzione da validare (status={self._status})")
            return False

        if start is None:
            errors.append("start_times è None nonostante lo status sia risolutivo.")
            _report(errors, warnings)
            return False

        # ── 1. Tutte le attività hanno un tempo di inizio ─────────────────────────

        missing = [i for i in range(n) if i not in start]
        if missing:
            errors.append(f"Attività senza start time: {missing}")

        # ── 2. Attività fittizia iniziale a t=0 ──────────────────────────────────

        if start.get(0, -1) != 0:
            errors.append(
                f"L'attività fittizia 0 deve iniziare a t=0, "
                f"trovato start[0]={start.get(0)}."
            )

        # ── 3. Makespan == start[n-1] ─────────────────────────────────────────────

        expected_makespan = start.get(n - 1)
        if inst.makespan != expected_makespan:
            errors.append(
                f"makespan={inst.makespan} != start[{n-1}]={expected_makespan}."
            )

        # ── 4. Durate, start e completamento validi ───────────────────────────────

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

        # ── 5. Vincoli di precedenza generalizzati ────────────────────────────────

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

        # ── 6. Release dates ──────────────────────────────────────────────────────

        if rd is not None:
            for i in range(n):
                if rd[i] is not None:
                    s = start.get(i)
                    if s is not None and s < rd[i]:
                        errors.append(
                            f"Attività {i}: start={s} < release_date={rd[i]}."
                        )

        # ── 7. Due dates ──────────────────────────────────────────────────────────

        if dd is not None:
            for i in range(n):
                if dd[i] is not None:
                    s = start.get(i)
                    if s is not None:
                        end_i = s + durations[i]
                        if end_i > dd[i]:
                            errors.append(
                                f"Attività {i}: end={end_i} > due_date={dd[i]} "
                                f"(start={s}, duration={durations[i]})."
                            )

        # ── 8. Vincoli di risorsa ─────────────────────────────────────────────────
        # Per ogni istante t in [0, makespan), somma i consumi delle attività attive.
        # Un'attività i è attiva in t se: start[i] <= t < start[i] + durations[i].
        # Le attività fittizie (durata=0) non contribuiscono.

        makespan_val = inst.makespan if inst.makespan is not None else horizon
        num_resources = len(resources)

        # Costruiamo un profilo di utilizzo per evento (più efficiente di un loop su t)
        for k in range(num_resources):
            # dizionario t → utilizzo cumulativo in t
            usage_events: dict[int, int] = {}

            for i in range(n):
                s = start.get(i)
                if s is None or durations[i] == 0:
                    continue
                c = consump[i][k]
                if c == 0:
                    continue
                # incrementa all'inizio, decrementa alla fine
                usage_events[s]                    = usage_events.get(s, 0) + c
                usage_events[s + durations[i]]     = usage_events.get(s + durations[i], 0) - c

            # scansione ordinata degli eventi → profilo a scalini
            current = 0
            for t in sorted(usage_events):
                current += usage_events[t]
                if current > resources[k]:
                    errors.append(
                        f"Risorsa {k}: utilizzo={current} > capacità={resources[k]} "
                        f"a t={t}."
                    )

        # ── Report finale ─────────────────────────────────────────────────────────

        _report(errors, warnings)
        return len(errors) == 0

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

if __name__ == "__main__":
    test = Test(dataset="tests/datasets/j120.sm/j1201_3.sm")
    test.build_model()
    test.solve_model()
    test.validate_solution()
