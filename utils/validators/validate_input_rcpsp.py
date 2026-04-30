"""
Funzione per validare gli input di un istanza rcpsp classica.
"""

from collections import defaultdict, deque
from utils.validators.minimum_checks import minimum_checks

def validate_inputs(classe) -> None:
    """
    Verifica la coerenza e ammissibilità degli input prima di costruire
    il modello. Rileva a priori le situazioni di inammissibilità strutturale
    evitando di avviare il solver su istanze non risolvibili.
    """
    activities = _get(classe, "activities")
    durations = _get(classe, "durations")
    precedences = _get(classe, "precedences")
    n = _get(classe, "n")
    resources = _get(classe, "resources")
    consumption = _get(classe ,"consumption")
    horizon = _get(classe, "horizon")

    minimum_checks(n, resources, durations, consumption, activities, horizon)

    # ── Validità degli archi di precedenza ───────────────────────────────
    valid_ids = set(activities)
    seen_edges = set()

    for idx, (i, j) in enumerate(precedences):

        # Indici fuori range
        if i not in valid_ids or j not in valid_ids:
            raise ValueError(
                f"Precedenza [{idx}] ({i} → {j}): uno o entrambi gli indici "
                f"sono fuori dal range [0, {n - 1}]."
            )

        # Auto-precedenza
        if i == j:
            raise ValueError(
                f"Precedenza [{idx}]: auto-precedenza sull'attività {i} "
                f"non ammessa."
            )

        # L'attività fittizia iniziale non può essere successore
        if j == 0:
            raise ValueError(
                f"Precedenza [{idx}]: l'attività fittizia iniziale (0) "
                f"non può essere successore di nessuna attività."
            )

        # L'attività fittizia finale non può essere predecessore
        if i == n - 1:
            raise ValueError(
                f"Precedenza [{idx}]: l'attività fittizia finale ({n - 1}) "
                f"non può essere predecessore di nessuna attività."
            )

        # Archi duplicati
        if (i, j) in seen_edges:
            raise ValueError(
                f"Precedenza [{idx}] ({i} → {j}): arco duplicato."
            )
        seen_edges.add((i, j))

    # ── Cicli nel grafo delle precedenze ─────────────────────────────────
    if _has_cycle(n, precedences):
        raise ValueError(
            "Il grafo delle precedenze contiene almeno un ciclo: "
            "il problema non ha soluzioni ammissibili."
        )
    
# ──────────────────────────────────────────────────────────────────────────────
# UTILITY — rilevamento cicli
# ──────────────────────────────────────────────────────────────────────────────

def _has_cycle(n: int, precedences: list[tuple[int, int]]) -> bool:
    """
    Rileva la presenza di cicli nel grafo delle precedenze tramite
    l'algoritmo di Kahn (ordinamento topologico BFS).
    Restituisce True se esiste almeno un ciclo, False altrimenti.
    """
    graph: dict[int, list[int]] = defaultdict(list)
    indegree = [0] * n

    for i, j in precedences:
        graph[i].append(j)
        indegree[j] += 1

    queue = deque(node for node in range(n) if indegree[node] == 0)
    visited = 0

    while queue:
        node = queue.popleft()
        visited += 1
        for neighbor in graph[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    return visited != n

def _get(classe, name):
    # prova prima con underscore
    if hasattr(classe, f"_{name}"):
        return getattr(classe, f"_{name}")
    # fallback senza underscore
    return getattr(classe, name)