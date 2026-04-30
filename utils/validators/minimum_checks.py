def minimum_checks(classe):
    m = len(classe._resources)

    # ── Dimensione minima ─────────────────────────────────────────────────
    if classe._n < 2:
        raise ValueError(
            "n deve essere almeno 2: sono richieste le due attività "
            "fittizie iniziale (0) e finale (n-1)."
        )
    
    # ── Attività fittizie ─────────────────────────────────────────────────
    if classe._durations[0] != 0 or classe._durations[classe._n - 1] != 0:
        raise ValueError(
            "Le attività fittizie 0 e n-1 devono avere durata 0."
        )
    
    # ── Vettore risorse ───────────────────────────────────────────────────
    if not isinstance(classe._resources, list):
        raise ValueError("resources deve essere una lista.")
    
    if len(classe._resources) == 0:
        raise ValueError("La lista resources non può essere vuota.")

    # ── Coerenza dimensionale dei vettori ─────────────────────────────────
    if len(classe._durations) != classe._n:
        raise ValueError(
            f"durations ha {len(classe._durations)} elementi, attesi {classe._n}."
        )

    if len(classe._consumption) != classe._n:
        raise ValueError(
            f"consumption ha {len(classe._consumption)} righe, attese {classe._n}."
        )

    for i, row in enumerate(classe._consumption):
        if len(row) != m:
            raise ValueError(
                f"consumption[{i}] ha {len(row)} colonne, attese {m} "
                f"(numero di risorse)."
            )

    # ── Valori non negativi sulle durate ──────────────────────────────────
    for i, d in enumerate(classe._durations):
        if d < 0:
            raise ValueError(
                f"durations[{i}] = {d}: le durate non possono essere negative."
            )

    # ── Disponibilità risorse strettamente positive ───────────────────────
    for k, r in enumerate(classe._resources):
        if r <= 0:
            raise ValueError(
                f"resources[{k}] = {r}: la disponibilità di ogni risorsa "
                f"deve essere > 0."
            )

    # ── Consumo non negativo e non eccedente la capacità ─────────────────
    # Un consumo già superiore alla capacità rende l'attività
    # inschedulabile a prescindere — inammissibilità rilevabile a priori.
    for i in classe._activities:
        for k, c in enumerate(classe._consumption[i]):
            if c < 0:
                raise ValueError(
                    f"consumption[{i}][{k}] = {c}: "
                    f"i consumi non possono essere negativi."
                )
            if c > classe._resources[k]:
                raise ValueError(
                    f"consumption[{i}][{k}] = {c} supera la disponibilità "
                    f"della risorsa {k} = {classe._resources[k]}: "
                    f"l'attività {i} non potrà mai essere schedulata."
                )

    # ── Attività fittizie ─────────────────────────────────────────────────
    if classe._durations[0] != 0 or classe._durations[classe._n - 1] != 0:
        raise ValueError(
            "Le attività fittizie 0 e n-1 devono avere durata 0."
        )

    if any(classe._consumption[0][k] != 0 for k in range(m)):
        raise ValueError(
            "L'attività fittizia iniziale (0) non deve consumare risorse."
        )

    if any(classe._consumption[classe._n - 1][k] != 0 for k in range(m)):
        raise ValueError(
            "L'attività fittizia finale (n-1) non deve consumare risorse."
        )

    # ── Horizon ──────────────────────────────────────────────────────────
    if classe._horizon <= 0:
        raise ValueError(
            f"horizon = {classe._horizon}: deve essere strettamente positiva."
        )
    
    # Lower bound banale: anche nel caso in cui tutte le attività si svolgessero 
    # in parallelo, il lower_bound è almeno uguale al massimo delle durate
    lower_bound = max(classe._durations)
    if classe._horizon < lower_bound:
        raise ValueError(
            f"horizon = {classe._horizon} è inferiore alla durata massima "
            f"({lower_bound}): il problema è strutturalmente inammissibile."
        )