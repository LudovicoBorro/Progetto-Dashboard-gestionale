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
        deadline = 667

        # Filling dei dati secondo il formato psplib
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
        
        self._model, starts = self._inst.build_model()
        if self._model != None:
            print("Modello correttamente creato!")
    
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
            print(self._inst.get_schedule)
        print(f"="*60)

if __name__ == "__main__":
    test = Test(dataset="tests/datasets/j120.sm/j1201_1.sm")
    test.build_model()
    test.solve_model()


    
