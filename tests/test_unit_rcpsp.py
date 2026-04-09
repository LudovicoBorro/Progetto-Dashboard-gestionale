"""
test_unit_rcpsp.py
------------------
Modulo per testare il modello rcpsp.py utilizzano dataset della libreria 
PSPLIB.
"""
from core.exact.rcpsp import Model
from psplib import parse
import time

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
        deadline = sum(a.modes[0].duration for a in self._instance.activities)

        # Fill dei dati secondo il formato psplib
        for i,a in enumerate(self._instance.activities):
            durations.append(a.modes[0].duration)
            consumption.append(a.modes[0].demands)
            
            for succ in a.successors:
                precedences.append((i, succ))

        for r in self._instance.resources:
            resources.append(r.capacity)

        self._inst = Model(n=numero_act, 
                            durations=durations, 
                            precedences=precedences,
                            resources=resources,
                            consumption=consumption,
                            deadline=deadline,
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
        del modello RCPSP classico:

            1. Soluzione disponibile
            2. Tutte le attività hanno un tempo di inizio
            3. Attività fittizia iniziale a t=0
            4. Makespan == start[n-1]
            5. Start non negativi e completamento entro deadline
            6. Vincoli di precedenza finish-to-start
            7. Vincoli di risorsa (nessuna violazione di capacità)
        """

        inst      = self._inst
        n         = inst._n
        durations = inst._durations
        start     = inst._start_times
        prec      = inst._precedences
        resources = inst._resources
        consump   = inst._consumption
        deadline  = inst._deadline

        errors = []

        # ── 1. Soluzione disponibile ──────────────────────────────────────────

        if self._status not in ("OPTIMAL", "FEASIBLE"):
            print(f"⚠️  Nessuna soluzione da validare (status={self._status})")
            return False

        if start is None:
            errors.append("start_times è None nonostante lo status sia risolutivo.")
            _report(errors)
            return False

        # ── 2. Tutte le attività hanno un tempo di inizio ─────────────────────

        missing = [i for i in range(n) if i not in start]
        if missing:
            errors.append(f"Attività senza start time: {missing}")

        # ── 3. Attività fittizia iniziale a t=0 ──────────────────────────────

        if start.get(0, -1) != 0:
            errors.append(
                f"L'attività fittizia 0 deve iniziare a t=0, "
                f"trovato start[0]={start.get(0)}."
            )

        # ── 4. Makespan == start[n-1] ─────────────────────────────────────────

        if inst.makespan != start.get(n - 1):
            errors.append(
                f"makespan={inst.makespan} != start[{n-1}]={start.get(n - 1)}."
            )

        # ── 5. Start non negativi e completamento entro deadline ──────────────

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

        # ── 6. Precedenze finish-to-start ─────────────────────────────────────
        # Vincolo: start[j] >= start[i] + durations[i]

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

        # ── 7. Vincoli di risorsa ─────────────────────────────────────────────
        # Profilo a eventi differenziali: O(n log n) invece di O(n × makespan).
        # Per ogni istante t in cui almeno un'attività è attiva,
        # il consumo cumulativo di ogni risorsa k non deve superare R[k].

        for k in range(len(resources)):
            # dizionario evento → variazione utilizzo
            delta: dict[int, int] = {}

            for i in range(n):
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

        # ── Report ────────────────────────────────────────────────────────────

        _report(errors)
        return len(errors) == 0
    
# ──────────────────────────────────────────────────────────────────────────────
# Helper — da tenere fuori dalla classe
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

if __name__ == "__main__":
    test = Test(dataset="tests/datasets/j120.sm/j1206_6.sm")
    test.build_model()
    test.solve_model()
    test.validate_solution()