from core.heuristics.sgs_engine_rcpsp_max import SGSEngine
from tests.instance_rcpsp_and_rcpsp_max import Instance
from core.heuristics.priority_rules import wrapper_rule

def debug_minimal():
    n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, horizon, consumption, release_dates, due_dates = Instance.get_raw_instance_with_intervals_minimal()
    
    # Fix to min durations for simplicity
    durations_fixed = [d[0] if isinstance(d, tuple) else d for d in durations]
    release_fixed = [r[0] if isinstance(r, tuple) else r for r in release_dates]
    due_fixed = [d[1] if isinstance(d, tuple) else d for d in due_dates]
    resources_fixed = [r[1] if isinstance(r, tuple) else r for r in resources]

    # Preprocessing
    from solver.preprocessing import _pre_processing_rcpsp_max
    proc = _pre_processing_rcpsp_max(n, durations_fixed, precedences_rcpsp_max, resources_fixed, consumption, horizon, release_fixed, due_fixed)
    
    sgs = SGSEngine(proc.n, proc.durations, proc.precedences, proc.resources, proc.consumption, proc.horizon, proc.release_dates, proc.due_dates, validate_input=False)
    
    pl = wrapper_rule("spt", proc.n, proc.durations, precedences_rcpsp_max=proc.precedences, resources=proc.resources, consumption=proc.consumption, horizon=proc.horizon)
    
    print(f"Total nodes (n): {proc.n}")
    print(f"Priority List: {pl}")
    print(f"Precedences: {proc.precedences}")
    
    sol = sgs.serial(pl, 1, 1, 1, 1, 100)
    
    print("\n--- SOLUTION ---")
    for act in sol:
        print(act)
    
    makespan = max(act['end'] for act in sol)
    print(f"\nMakespan: {makespan}")

if __name__ == "__main__":
    debug_minimal()
