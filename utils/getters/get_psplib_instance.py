"""
Modulo che contiene funzioni per ottenere istanze di problemi RCPSP/RCPSP_MAX da file in formato PSPLIB.
"""
from psplib import parse
import random

def get_psplib_instance(dataset, rcpsp_max=False):

    instance = parse(dataset, instance_format="psplib")

    numero_act = instance.num_activities
    durations = []
    consumption = []
    resources = []
    precedences = []
    horizon = sum(a.modes[0].duration for a in instance.activities)

    # Fill dei dati secondo il formato psplib
    for i,a in enumerate(instance.activities):
        durations.append(a.modes[0].duration)
        consumption.append(a.modes[0].demands)

    for r in instance.resources:
        resources.append(r.capacity)
    
    if rcpsp_max:
        release_dates = []
        due_dates = []
        for i,a in enumerate(instance.activities):
            release_dates.append(_sample_release_date(i, horizon, numero_act))
            due_dates.append(_sample_due_date(i, a, horizon, numero_act))
            precedences.extend(_build_precedences(i, a))

        return instance.activities, numero_act, durations, precedences, resources, consumption, horizon, release_dates, due_dates
    else:
        for i, a in enumerate(instance.activities):
            for succ in a.successors:
                precedences.append((i, succ))
    
        return instance.activities, numero_act, durations, precedences, resources, consumption, horizon

def _sample_release_date(i, horizon, numero_act):
    if i == 0:
        return 0
    if i == numero_act - 1:
        return None
    if random.random() < 0.4:
        return random.randint(0, int(0.3 * horizon))
    return None

def _sample_due_date(i, a, horizon, numero_act):
    if i == 0 or i == numero_act - 1:
        return None
    if random.random() < 0.5:
        base = random.randint(int(0.3 * horizon), int(0.7 * horizon))
        slack = random.randint(0, 2 * a.modes[0].duration)
        return base + slack
    return None

def _build_precedences(i, a):
    return [
        (i, succ, random.randint(0, max(1, a.modes[0].duration // 3)), None)
        for succ in a.successors
    ]