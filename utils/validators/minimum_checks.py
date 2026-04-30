def minimum_checks(n, resources, durations, consumption, activities, horizon):
    m = len(resources)

    # ── Dimensione minima ─────────────────────────────────────────────────
    if n < 2:
        raise ValueError(
            "n deve essere almeno 2: sono richieste le due attività "
            "fittizie iniziale (0) e finale (n-1)."
        )
    
    # ── Attività fittizie ─────────────────────────────────────────────────
    if durations[0] != 0 or durations[n - 1] != 0:
        raise ValueError(
            "Le attività fittizie 0 e n-1 devono avere durata 0."
        )
    
    # ── Vettore risorse ───────────────────────────────────────────────────
    if not isinstance(resources, list):
        raise ValueError("resources deve essere una lista.")
    
    if len(resources) == 0:
        raise ValueError("La lista resources non può essere vuota.")

    # ── Coerenza dimensionale dei vettori ─────────────────────────────────
    if len(durations) != n:
        raise ValueError(
            f"durations ha {len(durations)} elementi, attesi {n}."
        )

    if len(consumption) != n:
        raise ValueError(
            f"consumption ha {len(consumption)} righe, attese {n}."
        )

    for i, row in enumerate(consumption):
        if len(row) != m:
            raise ValueError(
                f"consumption[{i}] ha {len(row)} colonne, attese {m} "
                f"(numero di risorse)."
            )

    # ── Valori non negativi sulle durate ──────────────────────────────────
    for i, d in enumerate(durations):
        if d < 0:
            raise ValueError(
                f"durations[{i}] = {d}: le durate non possono essere negative."
            )

    # ── Disponibilità risorse strettamente positive ───────────────────────
    for k, r in enumerate(resources):
        if r <= 0:
            raise ValueError(
                f"resources[{k}] = {r}: la disponibilità di ogni risorsa "
                f"deve essere > 0."
            )

    # ── Consumo non negativo e non eccedente la capacità ─────────────────
    # Un consumo già superiore alla capacità rende l'attività
    # inschedulabile a prescindere — inammissibilità rilevabile a priori.
    for i in activities:
        for k, c in enumerate(consumption[i]):
            if c < 0:
                raise ValueError(
                    f"consumption[{i}][{k}] = {c}: "
                    f"i consumi non possono essere negativi."
                )
            if c > resources[k]:
                raise ValueError(
                    f"consumption[{i}][{k}] = {c} supera la disponibilità "
                    f"della risorsa {k} = {resources[k]}: "
                    f"l'attività {i} non potrà mai essere schedulata."
                )

    # ── Attività fittizie ─────────────────────────────────────────────────
    if durations[0] != 0 or durations[n - 1] != 0:
        raise ValueError(
            "Le attività fittizie 0 e n-1 devono avere durata 0."
        )

    if any(consumption[0][k] != 0 for k in range(m)):
        raise ValueError(
            "L'attività fittizia iniziale (0) non deve consumare risorse."
        )

    if any(consumption[n - 1][k] != 0 for k in range(m)):
        raise ValueError(
            "L'attività fittizia finale (n-1) non deve consumare risorse."
        )

    # ── Horizon ──────────────────────────────────────────────────────────
    if horizon <= 0:
        raise ValueError(
            f"horizon = {horizon}: deve essere strettamente positiva."
        )
    
    # Lower bound banale: anche nel caso in cui tutte le attività si svolgessero 
    # in parallelo, il lower_bound è almeno uguale al massimo delle durate
    lower_bound = max(durations)
    if horizon < lower_bound:
        raise ValueError(
            f"horizon = {horizon} è inferiore alla durata massima "
            f"({lower_bound}): il problema è strutturalmente inammissibile."
        )