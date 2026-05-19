def calculate_expected_progress(start_time: int, duration: int, today_idx: int) -> float:
    
    elapsed_days = today_idx - start_time

    if elapsed_days < 0:
        return 0.0
    
    if elapsed_days > duration:
        return 1.0

    expected_progress = elapsed_days / duration
    return max(0.0, min(1.0, expected_progress))

def calculate_schedule_variance(actual_progress: float, expected_progress: float) -> float:
    return actual_progress - expected_progress

