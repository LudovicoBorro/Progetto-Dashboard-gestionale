from solver.orchestrator import SolverOrchestrator
from tests.instance_rcpsp_and_rcpsp_max import Instance
import json

def debug_minimal_bb():
    n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, horizon, consumption, release_dates, due_dates = Instance.get_raw_instance_with_intervals_minimal()
    
    so = SolverOrchestrator()
    print("Inizio debug minimal B&B...")
    
    # Lancio il modello e prendo la migliore soluzione trovata al nodo radice (o quella finale)
    res = so.choose_model(
        n, durations, precedences_rcpsp_max, resources, consumption, horizon, 
        release_dates, due_dates, instant_sol=True, rcpsp_max=True, top_k=5, has_intervals=True
    )
    
    best_sol = res.solution.best.get('best')
    print("\n--- SOLUZIONE MIGLIORE ---")
    print(f"Makespan: {best_sol.get('makespan')}")
    print(f"Penalità totale: {best_sol.get('penalità')}")
    print(f"Score: {best_sol.get('score')}")
    print("\nDettaglio attività:")
    for act in best_sol.get('soluzione'):
        print(f"Act {act['activity']}: [{act['start']}, {act['end']}] | Penalty: {act['penalty']}")

    # Verifichiamo i vincoli manualmente
    print("\n--- VERIFICA VINCOLI ---")
    # Precedenze shiftate e convertite
    from solver.preprocessing import _pre_processing_rcpsp_max
    # Usiamo la configurazione migliore trovata
    config = res.config
    proc = _pre_processing_rcpsp_max(n, config.durations, precedences_rcpsp_max, config.resources, consumption, horizon, config.release_dates, config.due_dates)
    
    act_map = {a['activity']: a for a in best_sol.get('soluzione')}
    
    for (i, j, min_lag, max_lag) in proc.precedences:
        si = act_map[i]['start']
        sj = act_map[j]['start']
        if sj < si + min_lag:
            print(f"VIOLAZIONE PRECEDENZA: ({i} -> {j}) | {sj} < {si} + {min_lag}")
        if max_lag and sj > si + max_lag:
            print(f"VIOLAZIONE MAX_LAG: ({i} -> {j}) | {sj} > {si} + {max_lag}")

    for i in range(proc.n):
        s = act_map[i]['start']
        e = act_map[i]['end']
        rd = proc.release_dates[i]
        dd = proc.due_dates[i]
        if rd and s < rd:
            print(f"VIOLAZIONE RELEASE DATE: Act {i} | {s} < {rd}")
        if dd and e > dd:
            print(f"VIOLAZIONE DUE DATE: Act {i} | {e} > {dd}")

if __name__ == "__main__":
    debug_minimal_bb()
