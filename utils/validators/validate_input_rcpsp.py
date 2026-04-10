"""
Funzione per validare gli input di un istanza rcpsp classica.
"""

from collections import defaultdict, deque

def validate_inputs(self) -> None:
    """
    Verifica la coerenza e ammissibilità degli input prima di costruire
    il modello. Rileva a priori le situazioni di inammissibilità strutturale
    evitando di avviare il solver su istanze non risolvibili.
    """
    m = len(self._resources)

    # ── Dimensione minima ─────────────────────────────────────────────────
    if self._n < 2:
        raise ValueError(
            "n deve essere almeno 2: sono richieste le due attività "
            "fittizie iniziale (0) e finale (n-1)."
        )

    # ── Coerenza dimensionale dei vettori ─────────────────────────────────
    if len(self._durations) != self._n:
        raise ValueError(
            f"durations ha {len(self._durations)} elementi, attesi {self._n}."
        )

    if len(self._consumption) != self._n:
        raise ValueError(
            f"consumption ha {len(self._consumption)} righe, attese {self._n}."
        )

    for i, row in enumerate(self._consumption):
        if len(row) != m:
            raise ValueError(
                f"consumption[{i}] ha {len(row)} colonne, attese {m} "
                f"(numero di risorse)."
            )

    # ── Valori non negativi sulle durate ──────────────────────────────────
    for i, d in enumerate(self._durations):
        if d < 0:
            raise ValueError(
                f"durations[{i}] = {d}: le durate non possono essere negative."
            )

    # ── Disponibilità risorse strettamente positive ───────────────────────
    for k, r in enumerate(self._resources):
        if r <= 0:
            raise ValueError(
                f"resources[{k}] = {r}: la disponibilità di ogni risorsa "
                f"deve essere > 0."
            )

    # ── Consumo non negativo e non eccedente la capacità ─────────────────
    # Un consumo già superiore alla capacità rende l'attività
    # inschedulabile a prescindere — inammissibilità rilevabile a priori.
    for i in self._activities:
        for k, c in enumerate(self._consumption[i]):
            if c < 0:
                raise ValueError(
                    f"consumption[{i}][{k}] = {c}: "
                    f"i consumi non possono essere negativi."
                )
            if c > self._resources[k]:
                raise ValueError(
                    f"consumption[{i}][{k}] = {c} supera la disponibilità "
                    f"della risorsa {k} = {self._resources[k]}: "
                    f"l'attività {i} non potrà mai essere schedulata."
                )

    # ── Attività fittizie ─────────────────────────────────────────────────
    if self._durations[0] != 0 or self._durations[self._n - 1] != 0:
        raise ValueError(
            "Le attività fittizie 0 e n-1 devono avere durata 0."
        )

    if any(self._consumption[0][k] != 0 for k in range(m)):
        raise ValueError(
            "L'attività fittizia iniziale (0) non deve consumare risorse."
        )

    if any(self._consumption[self._n - 1][k] != 0 for k in range(m)):
        raise ValueError(
            "L'attività fittizia finale (n-1) non deve consumare risorse."
        )

    # ── Deadline ──────────────────────────────────────────────────────────
    if self._deadline <= 0:
        raise ValueError(
            f"deadline = {self._deadline}: deve essere strettamente positiva."
        )

    # Lower bound banale: anche nel caso in cui tutte le attività si svolgessero 
    # in parallelo, il lower_bound è almeno uguale al massimo delle durate
    lower_bound = max(self._durations)
    if self._deadline < lower_bound:
        raise ValueError(
            f"deadline = {self._deadline} è inferiore alla durata massima "
            f"({lower_bound}): il problema è strutturalmente inammissibile."
        )

    # ── Validità degli archi di precedenza ───────────────────────────────
    valid_ids = set(self._activities)
    seen_edges = set()

    for idx, (i, j) in enumerate(self._precedences):

        # Indici fuori range
        if i not in valid_ids or j not in valid_ids:
            raise ValueError(
                f"Precedenza [{idx}] ({i} → {j}): uno o entrambi gli indici "
                f"sono fuori dal range [0, {self._n - 1}]."
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
        if i == self._n - 1:
            raise ValueError(
                f"Precedenza [{idx}]: l'attività fittizia finale ({self._n - 1}) "
                f"non può essere predecessore di nessuna attività."
            )

        # Archi duplicati
        if (i, j) in seen_edges:
            raise ValueError(
                f"Precedenza [{idx}] ({i} → {j}): arco duplicato."
            )
        seen_edges.add((i, j))

    # ── Cicli nel grafo delle precedenze ─────────────────────────────────
    if _has_cycle(self._n, self._precedences):
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