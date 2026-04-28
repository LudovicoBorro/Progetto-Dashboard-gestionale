def minimum_checks(self):
    m = len(self._resources)

    # ── Dimensione minima ─────────────────────────────────────────────────
    if self._n < 2:
        raise ValueError(
            "n deve essere almeno 2: sono richieste le due attività "
            "fittizie iniziale (0) e finale (n-1)."
        )
    
    # ── Attività fittizie ─────────────────────────────────────────────────
    if self._durations[0] != 0 or self._durations[self._n - 1] != 0:
        raise ValueError(
            "Le attività fittizie 0 e n-1 devono avere durata 0."
        )
    
    # ── Vettore risorse ───────────────────────────────────────────────────
    if not isinstance(self._resources, list):
        raise ValueError("resources deve essere una lista.")
    
    if len(self._resources) == 0:
        raise ValueError("La lista resources non può essere vuota.")

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

    # ── Horizon ──────────────────────────────────────────────────────────
    if self._horizon <= 0:
        raise ValueError(
            f"horizon = {self._horizon}: deve essere strettamente positiva."
        )
    
    # Lower bound banale: anche nel caso in cui tutte le attività si svolgessero 
    # in parallelo, il lower_bound è almeno uguale al massimo delle durate
    lower_bound = max(self._durations)
    if self._horizon < lower_bound:
        raise ValueError(
            f"horizon = {self._horizon} è inferiore alla durata massima "
            f"({lower_bound}): il problema è strutturalmente inammissibile."
        )