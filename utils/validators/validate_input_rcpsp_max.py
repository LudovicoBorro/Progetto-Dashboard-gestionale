"""
Funzione per validare gli input di un istanza rcpsp/max.
"""

from utils.validators.minimum_checks import minimum_checks

def validate_inputs(classe):
    """
    Verifica la coerenza e ammissibilità degli input prima di costruire
    il modello. Rileva a priori le situazioni di inammissibilità strutturale
    evitando di avviare il solver su istanze non risolvibili.
    """
    activities = _get(classe, "activities")
    durations = _get(classe, "durations")
    precedences = _get(classe, "precedences")
    release_dates = _get(classe, "release_dates")
    due_dates = _get(classe, "due_dates")
    n = _get(classe, "n")
    resources = _get(classe, "resources")
    consumption = _get(classe ,"consumption")
    horizon = _get(classe, "horizon")
    
    minimum_checks(n, resources, durations, consumption, activities, horizon)
    
    # ── Validazione su release_dates e due_dates ─────────────────────────
    if release_dates is not None and due_dates is not None:
        for i in activities:
            if release_dates[i] is not None and due_dates[i] is not None:
                if release_dates[i] > due_dates[i] - durations[i]:
                    raise ValueError(
                        f"{release_dates[i]} non valida per l'attività {i}, "
                        f"non garantisce che la data di scadenza sia rispettata: "
                        f"l'attività {i} non potrà mai essere schedulata."
                    )
    
    # ── Validità degli archi di precedenza ───────────────────────────────
    valid_ids = set(activities)
    seen_edges = set()

    for idx, (i, j, min_lag, max_lag) in enumerate(precedences):

        # ── Indici validi ─────────────────────────────
        if i not in valid_ids or j not in valid_ids:
            raise ValueError(
                f"Precedenza [{idx}] ({i} → {j}): indici fuori range."
            )

        # ── Auto-loop ────────────────────────────────
        if i == j:
            raise ValueError(
                f"Precedenza [{idx}]: self-loop non ammesso ({i} → {j})."
            )

        # ── Dummy nodes ──────────────────────────────
        if j == 0:
            raise ValueError(
                f"Precedenza [{idx}]: attività 0 non può essere successore."
            )

        if i == n - 1:
            raise ValueError(
                f"Precedenza [{idx}]: attività finale non può essere predecessore."
            )

        # ── min_lag ─────────────────────────────────
        if min_lag is None:
            raise ValueError(
                f"Precedenza [{idx}] ({i} → {j}): min_lag mancante."
            )

        # ── max_lag ─────────────────────────────────
        if max_lag is not None and max_lag < min_lag:
            raise ValueError(
                f"Precedenza [{idx}] ({i} → {j}): max_lag < min_lag."
            )

        # ── duplicati ───────────────────────────────
        if (i, j) in seen_edges:
            raise ValueError(
                f"Precedenza duplicata ({i} → {j})."
            )
        seen_edges.add((i, j))

    # ── Cicli nel grafo delle precedenze ─────────────────────────────────
    _check_time_feasibility(precedences, n)
    
    # ── Release e due date validation ────────────────────────────────────
    if release_dates is not None and len(release_dates) != n:
        raise ValueError("release_dates dimensione errata")

    if due_dates is not None and len(due_dates) != n:
        raise ValueError("due_dates dimensione errata")

# ──────────────────────────────────────────────────────────────────────────────
# UTILITY — rilevamento cicli
# ──────────────────────────────────────────────────────────────────────────────
    
def _check_time_feasibility(precedences, n):
    """
    Verifica che i vincoli di tipo:
        start[j] ≥ start[i] + min_lag
        start[j] ≤ start[i] + max_lag
    siano consistenti.
    """

    # trasformiamo tutto in:
    # start[j] ≥ start[i] + w
    edges = []

    for (i, j, min_lag, max_lag) in precedences:
        edges.append((i, j, min_lag))
        if max_lag is not None:
            edges.append((j, i, -max_lag))

    dist = [0] * n

    # Bellman-Ford
    for _ in range(n):
        updated = False
        for u, v, w in edges:
            if dist[v] < dist[u] + w:
                dist[v] = dist[u] + w
                updated = True
        if not updated:
            return

    # se ancora aggiornabile → ciclo positivo
    raise ValueError(
        "Vincoli temporali inconsistenti (positive cycle nei time-lag)."
    )

def _get(classe, name):
    # prova prima con underscore
    if hasattr(classe, f"_{name}"):
        return getattr(classe, f"_{name}")
    # fallback senza underscore
    return getattr(classe, name)