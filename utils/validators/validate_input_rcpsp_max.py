"""
Funzione per validare gli input di un istanza rcpsp/max.
"""

def validate_inputs(self):
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
    
    # ── Validazione su release_dates e due_dates ─────────────────────────
    if self._release_dates is not None and self._due_dates is not None:
        for i in self._activities:
            if self._release_dates[i] is not None and self._due_dates[i] is not None:
                if self._release_dates[i] > self._due_dates[i] - self._durations[i]:
                    raise ValueError(
                        f"{self._release_dates[i]} non valida per l'attività {i}, "
                        f"non garantisce che la data di scadenza sia rispettata: "
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
    if self._horizon <= 0:
        raise ValueError(
            f"deadline = {self._horizon}: deve essere strettamente positiva."
        )

    # Lower bound banale: anche nel caso in cui tutte le attività si svolgessero 
    # in parallelo, il lower_bound è almeno uguale al massimo delle durate
    lower_bound = max(self._durations)
    if self._horizon < lower_bound:
        raise ValueError(
            f"deadline = {self._horizon} è inferiore alla durata massima "
            f"({lower_bound}): il problema è strutturalmente inammissibile."
        )
    
    # ── Validità degli archi di precedenza ───────────────────────────────
    valid_ids = set(self._activities)
    seen_edges = set()

    for idx, (i, j, min_lag, max_lag) in enumerate(self._precedences):

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

        if i == self._n - 1:
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
    _check_time_feasibility(self._precedences, self._n)
    
    # ── Release e due date validation ────────────────────────────────────
    if self._release_dates is not None:
        if len(self._release_dates) != self._n:
            raise ValueError("release_dates dimensione errata")

    if self._due_dates is not None:
        if len(self._due_dates) != self._n:
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