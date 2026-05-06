import time
import os
import sys
from solver.orchestrator import SolverOrchestrator
from tests.instance_rcpsp_and_rcpsp_max import Instance
from solver.preprocessing import _pre_processing_rcpsp_max, _pre_processing_rcpsp


# Comando da lanciare per lo stress test:
# $env:PYTHONPATH="."; python scratch/stress_test_orchestrator.py cat scratch/stress_test_results.txt

# Configurazione logging
LOG_FILE = os.path.join("scratch", "stress_test_results.txt")

def log(message, to_file=True):
    print(message)
    if to_file:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")

def clear_log():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("=== RCPSP/MAX SOLVER STRESS TEST REPORT ===\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

class SolutionValidator:
    @staticmethod
    def validate(n, durations, precedences, resources, consumption, solution, release_dates=None, due_dates=None):
        errors = []
        
        # 1. Completezza
        scheduled_activities = {act['activity'] for act in solution}
        if len(scheduled_activities) != n:
            errors.append(f"Incomplete: {len(scheduled_activities)}/{n} activities.")
        
        starts = {act['activity']: act['start'] for act in solution}
        ends = {act['activity']: act['end'] for act in solution}
        
        # 2. Durate
        for act in solution:
            idx = act['activity']
            actual_dur = act['end'] - act['start']
            expected_dur = durations[idx]
            if actual_dur != expected_dur:
                errors.append(f"Act {idx}: dur {actual_dur} != exp {expected_dur}")

        # 3. Precedenze
        for (i, j, min_lag, max_lag) in precedences:
            if i in starts and j in starts:
                if starts[j] < starts[i] + min_lag:
                    errors.append(f"Prec {i}->{j}: start_{j}({starts[j]}) < s_{i}+{min_lag}({starts[i]+min_lag})")
                if max_lag is not None and starts[j] > starts[i] + max_lag:
                    errors.append(f"Prec {i}->{j}: start_{j}({starts[j]}) > s_{i}+{max_lag}({starts[i]+max_lag})")

        # 4. Risorse
        if ends:
            max_t = max(ends.values())
            for t in range(max_t):
                for r_idx, cap in enumerate(resources):
                    usage = sum(consumption[act['activity']][r_idx] for act in solution if act['start'] <= t < act['end'])
                    if usage > cap:
                        errors.append(f"Time {t}, Res {r_idx}: usage {usage} > cap {cap}")
                        break

        # 5. Release Dates
        if release_dates:
            for i, rd in enumerate(release_dates):
                if rd is not None and i in starts and starts[i] < rd:
                    errors.append(f"Act {i}: start {starts[i]} < release {rd}")

        return errors

def run_orchestrator_test(test_id, name, data_func, **params):
    log(f"\n[{test_id}] TEST CASE: {name}")
    log("-" * 50)
    log(f"Parameters: {params}")
    
    raw = data_func()
    n, _, durations, resources, prec_rcpsp, prec_max, horizon, consumption, rd, dd = raw
    
    so = SolverOrchestrator()
    start_t = time.time()
    
    try:
        res = so.choose_model(
            n, durations, prec_max if params.get('rcpsp_max', True) else prec_rcpsp,
            resources, consumption, horizon, rd, dd, **params
        )
        elapsed = time.time() - start_t
        
        # Estrazione dati per validazione
        if isinstance(res, dict):
            best_sol_wrapper = res.get('best', {})
            res_type = res.get('type', '')
            if res_type == 'exact':
                # Il modello esatto ha struttura diversa: res['best'] = {'solution':{}, 'makespan': int, 'schedule': [...], ...}
                # Non c'è una chiave 'best' annidata, la schedule è in 'schedule' non in 'soluzione'
                if isinstance(best_sol_wrapper, dict) and best_sol_wrapper.get('makespan') is not None:
                    best_sol = {
                        'makespan': best_sol_wrapper.get('makespan'),
                        'penalità': None,
                        'soluzione': best_sol_wrapper.get('schedule', [])
                    }
                else:
                    best_sol = None
            else:
                # Modello euristico o fallback: res['best']['best'] contiene la soluzione
                best_sol = best_sol_wrapper.get('best') if isinstance(best_sol_wrapper, dict) else best_sol_wrapper
            val_dur = durations
            val_res = resources
            val_rd, val_dd = rd, dd
        else:
            best_sol = res.solution.best.get('best')
            val_dur = res.config.durations
            val_res = res.config.resources
            val_rd, val_dd = res.config.release_dates, res.config.due_dates

        if not best_sol:
            log(f"RESULT: FAILED (No solution found, Time: {elapsed:.2f}s)")
            return False

        log(f"RESULT: SUCCESS (Makespan: {best_sol.get('makespan')}, Penalty: {best_sol.get('penalità')}, Time: {elapsed:.2f}s)")
        
        # Preprocessing per validazione (grafi espansi)
        if params.get('rcpsp_max', True):
            proc = _pre_processing_rcpsp_max(n, val_dur, prec_max, val_res, consumption, horizon, val_rd, val_dd)
            v_prec = proc.precedences
            v_n, v_dur, v_res, v_cons, v_rd, v_dd = proc.n, proc.durations, proc.resources, proc.consumption, proc.release_dates, proc.due_dates
        else:
            proc = _pre_processing_rcpsp(n, val_dur, prec_rcpsp, val_res, consumption, horizon)
            v_prec = [(i, j, proc.durations[i], None) for i, j in proc.precedences]
            v_n, v_dur, v_res, v_cons, v_rd, v_dd = proc.n, proc.durations, proc.resources, proc.consumption, None, None

        errors = SolutionValidator.validate(v_n, v_dur, v_prec, v_res, v_cons, best_sol['soluzione'], v_rd, v_dd)
        
        if errors:
            log(f"VALIDATION: FAILED ({len(errors)} errors)")
            for e in errors[:5]: log(f"  !! {e}")
            return False
        else:
            log("VALIDATION: PASSED")
            return True

    except Exception as e:
        log(f"RESULT: CRASHED ({type(e).__name__}: {e})")
        import traceback
        with open(LOG_FILE, "a") as f:
            traceback.print_exc(file=f)
        return False

if __name__ == "__main__":
    if not os.path.exists("scratch"): os.makedirs("scratch")
    clear_log()
    
    suite_start = time.time()
    tests = [
        # 1. Base RCPSP/Max (Heuristic)
        ("H1", "Standard RCPSP/Max (Heuristic)", Instance.get_raw_instance, {"instant_sol": True, "rcpsp_max": True}),
        
        # 2. Base RCPSP Classic (Heuristic)
        ("H2", "Standard RCPSP Classic (Heuristic)", Instance.get_raw_instance, {"instant_sol": True, "rcpsp_max": False}),
        
        # 3. Intervals Minimal (B&B)
        ("B1", "Intervals Minimal (B&B)", Instance.get_raw_instance_with_intervals_minimal, {"instant_sol": False, "has_intervals": True, "rcpsp_max": True}),
        
        # 4. Intervals Large (Fast B&B)
        ("B2", "Intervals Large (Fast B&B)", Instance.get_raw_instance_with_intervals, {"instant_sol": True, "has_intervals": True, "rcpsp_max": True}),
        
        # 5. Weight Variations (Resource focus)
        ("W1", "Weight Variation (Res focus)", Instance.get_raw_instance, {"instant_sol": True, "rcpsp_max": True, "resource_weight": 5, "time_weight": 0.1}),
        
        # 6. Priority Rule Variations
        ("P1", "Priority Rule (MTS)", Instance.get_raw_instance, {"instant_sol": True, "rcpsp_max": True, "priority_rule": "mts"}),
        ("P2", "Priority Rule (GRD)", Instance.get_raw_instance, {"instant_sol": True, "rcpsp_max": True, "priority_rule": "grd"}),
        
        # 7. Exact Model Fallback (Classic)
        ("E1", "Exact Model (Classic)", Instance.get_raw_instance, {"instant_sol": False, "rcpsp_max": False}),
    ]
    
    passed = 0
    for t_id, name, func, params in tests:
        if run_orchestrator_test(t_id, name, func, **params):
            passed += 1
    
    suite_elapsed = time.time() - suite_start
    summary = f"\n{'='*50}\nFINAL SUMMARY: {passed}/{len(tests)} tests passed\nTotal Suite Time: {suite_elapsed:.2f}s\n{'='*50}"
    log(summary)
