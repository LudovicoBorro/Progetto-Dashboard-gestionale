from collections import deque

def spt_list(activities: list[int], durations: list[int]):
    """
    Regola di priorità SPT (Shortest Process Time), valida 
    sia per il problema rcpsp classico sia per rcpsp/max.

    È basata sulle caratteristiche intrinseche delle 
    attività del progetto (activity-based).

    Le attività vengon ordinate in modo non decrescente 
    rispetto alla loro durata, dando la precedenza ai
    job più brevi.

    Restituisce:
        - priority_list = [j_1, j_2, ....]
    """
    return sorted(activities, key=lambda j: durations[j])

def mts_list(n: int, precedences: list[tuple[int, int]]):
    """
    Regola di priorità MTS (Most Total Successors),
    valida sia per il problema rcpsp classico sia per
    rcpsp/max. 

    È basata sulla logica della rete (network-based).

    Assegna la priorità alle attività che hanno il
    maggior numero totale di successori, sia diretti
    che indiretti, all'interno del grafo di progetto.
    L'idea è di completare il prima possibile le attività
    con tanti successori, in modo da sbloccare il maggior
    numero possibile di task successivi.

    Restituisce:
        - priority_list = [j_1, j_2, ....]
    """
    succ_map = {i: [] for i in range(n)}
    indegree = [0] * n

    for i, j in precedences:
        succ_map[i].append(j)
        indegree[j] += 1

    # topological order
    queue = deque([i for i in range(n) if indegree[i] == 0])
    topo = []

    while queue:
        u = queue.popleft()
        topo.append(u)
        for v in succ_map[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)

    # DP backward
    succ_sets = [set() for _ in range(n)]

    for j in reversed(topo):
        for k in succ_map[j]:
            succ_sets[j].add(k)
            succ_sets[j] |= succ_sets[k]

    MTS = [len(succ_sets[j]) for j in range(n)]

    return sorted(range(n), key=lambda j: MTS[j], reverse=True)

def grd_list(n: int, consumption: list[list[int]], resources: list[int]):
    """
    Regola di priorità GRD (Greatest Resource Demand),
    valida sia per rcpsp classico sia per rcpsp/max.

    È basata sulla richiesta di risorse delle attività
    rispetto alla disponibilità del sistema (resource-based).

    Assegna la precedenza alle attività che hanno il maggior
    carico di lavoro sulle risorse. L'idea è di schedulare
    prima i task più "pesanti" o critici dal punto di vista
    dell'assorbimento di capacità, per evitare che diventino
    dei colli di bottiglia nelle fasi avanzate del progetto.

    Restituisce:
        - priority_list = [j_1, j_2, ....]
    """

    GRD = []

    for j in range(n):
        score = sum(
            consumption[j][r] / resources[r]
            for r in range(len(resources))
            if resources[r] > 0
        )
        GRD.append(score)

    return sorted(range(n), key=lambda j: GRD[j], reverse=True)

def lft_list_rcpsp(
        n: int,
        durations: list[int],
        precedences: list[tuple[int, int]],
        horizon: int
):
    """
    Regola di priorità LFT (Latest Finishing Time),
    valida solamente per il problema rcpsp classico.
    
    È basata sul cammino critico (CP).

    Le attività vengono ordinate nella lista in modo 
    non decrescente rispetto al loro LF_i, cioè il
    Latest Finish, l'istante di fine più tardo, in 
    cui l'attività i può terminare senza ritardare
    la durata minima del progetto.

    Restituisce:
        - priority_list = [j_1, j_2, ....]
    """
    
    # Successori
    succ_map = {i: [] for i in range(n)}
    indegree = [0] * n

    for i, j in precedences:
        succ_map[i].append(j)
        indegree[j] += 1

    # Topological order
    queue = deque([i for i in range(n) if indegree[i] == 0])
    topo = []

    while queue:
        u = queue.popleft()
        topo.append(u)
        for v in succ_map[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)

    # Backward pass
    LFT = [float("inf")] * n
    last = topo[-1]
    LFT[last] = horizon

    for j in reversed(topo):
        if succ_map[j]:
            LFT[j] = min(
                LFT[k] - durations[j]
                for k in succ_map[j]
            )

    # Priority list
    return sorted(range(n), key=lambda j: LFT[j])

def lft_list_rcpsp_max(
        n: int,
        durations: list[int],
        precedences: list[tuple[int, int, int, int | None]],
        horizon: int
):
    """
    Regola di priorità LFT (Latest Finishing Time),
    valida solamente per il problema rcpsp/max.
    
    È basata sul cammino critico (CP).

    Le attività vengono ordinate nella lista in modo 
    non decrescente rispetto al loro LF_i, cioè il
    Latest Finish, l'istante di fine più tardo, in 
    cui l'attività i può terminare senza ritardare
    la durata minima del progetto.

    Restituisce:
        - priority_list = [j_1, j_2, ....]
    """
    succ_map = {i: [] for i in range(n)}

    # Considero solo il min_lag, poichè Belmann-Ford 
    # divergerebbe molto facilmente se ci sono cicli nel grafo
    for i, j, min_lag, _ in precedences:
        succ_map[i].append((j, min_lag))

    LST = [horizon] * n
    LST[n - 1] = horizon

    for j in reversed(range(n)):
        if succ_map[j]:
            LST[j] = min(
                LST[k] - lag
                for (k, lag) in succ_map[j]
            )

    LFT = [LST[j] + durations[j] for j in range(n)]

    return sorted(range(n), key=lambda j: LFT[j])

def lst_list_rcpsp(
        n: int,
        durations: list[int],
        precedences: list[tuple[int, int]],
        horizon: int
):
    """
    Regola di priorità LST (Latest Starting Time),
    valida solamente per il problema rcpsp classico.
    
    È basata sul cammino critico (CP).

    Le attività vengono ordinate nella lista in modo 
    non decrescente rispetto al loro LS_i, cioè il
    Latest Start, l'istante di inizio più tardo, entro
    il quale l'attività i deve iniziare per non ritardare
    l'intero progetto.

    Restituisce:
        - priority_list = [j_1, j_2, ....]
    """
    # Costruzione successori
    succs = {i: [] for i in range(n)}
    for i, j in precedences:
        succs[i].append(j)

    # Inizializzazione LFT
    LFT = {i: horizon for i in range(n)}
    last = n - 1
    LFT[last] = horizon  # nodo finale

    # Backward pass (CPM)
    changed = True
    while changed:
        changed = False
        for i in range(n):
            for j in succs[i]:
                if LFT[i] > LFT[j] - durations[j]:
                    LFT[i] = LFT[j] - durations[j]
                    changed = True

    # Calcolo LST
    LST = {i: LFT[i] - durations[i] for i in range(n)}

    return sorted(range(n), key=lambda x: LST[x])

def lst_list_rcpsp_max(
        n: int,
        durations: list[int],
        precedences: list[tuple[int, int, int, int | None]],
        horizon: int
):
    """
    Regola di priorità LST (Latest Starting Time),
    valida solamente per il problema rcpsp/max.
    
    È basata sul cammino critico (CP).

    Le attività vengono ordinate nella lista in modo 
    non decrescente rispetto al loro LS_i, cioè il
    Latest Start, l'istante di inizio più tardo, entro
    il quale l'attività i deve iniziare per non ritardare
    l'intero progetto.

    Restituisce:
        - priority_list = [j_1, j_2, ....]
    """
    # Costruzione successori
    succs = {i: [] for i in range(n)}
    for i, j, min_lag, _ in precedences:
        succs[i].append((j, min_lag))

    # Inizializzazione LFT
    LFT = {i: horizon for i in range(n)}
    last = n - 1
    LFT[last] = horizon

    # Backward pass (tipo CPM ma su start)
    changed = True
    while changed:
        changed = False
        for i in range(n):
            for j, min_lag in succs[i]:
                if LFT[i] > LFT[j] - min_lag:
                    LFT[i] = LFT[j] - min_lag
                    changed = True

    # Calcolo LST
    LST = {i: LFT[i] - durations[i] for i in range(n)}

    return sorted(range(n), key=lambda x: LST[x])

def mslk_list_rcpsp(
        n: int,
        durations: list[int],
        precedences: list[tuple[int, int]],
        horizon: int
):
    """
    Regola di priorità MSLK (Minimum Slack Time), valida
    solamente per rcpsp classico.

    È basata sul cammino critico (CP).

    Le attività vengono ordinate nella lista in modo non
    decrescente in base al loro slack, calcolato come:
        Slack_j = LF_j - EF_j
    Le attività con valori di slack alti sono meno urgenti
    e più flessibili, quelle con valori si slack bassi o
    prossimi allo zero hanno una priorità alta e quindi sono
    task critici. Se lo slack è negativo l'attività j è 
    in ritardo.

    Restituisce:
        - priority_list = [j_1, j_2, ....]
    """
    # Costruzione grafo
    succs = {i: [] for i in range(n)}
    preds = {i: [] for i in range(n)}

    for i, j in precedences:
        succs[i].append(j)
        preds[j].append(i)

    # Forward pass per EST (Earliest Starting Time)
    EST = [0] * n

    changed = True
    while changed:
        changed = False
        for j in range(n):
            for i in preds[j]:
                val = EST[i] + durations[i]
                if EST[j] < val:
                    EST[j] = val
                    changed = True

    # Backward pass per LFT (Latest Finishing Time)
    LFT = [horizon] * n
    LFT[n - 1] = horizon

    changed = True
    while changed:
        changed = False
        for i in range(n):
            for j in succs[i]:
                val = LFT[j] - durations[j]
                if LFT[i] > val:
                    LFT[i] = val
                    changed = True

    # Calcolo LST (Latest Starting Time)
    LST = [LFT[i] - durations[i] for i in range(n)]

    # Calcolo Slack
    SLK = [LST[i] - EST[i] for i in range(n)]

    return sorted(range(n), key=lambda x: SLK[x])

def mslk_list_rcpsp_max(
        n: int,
        durations: list[int],
        precedences: list[tuple[int, int, int, int | None]],
        horizon: int
):
    """
    Regola di priorità MSLK (Minimum Slack Time), valida
    solamente per rcpsp/max.

    È basata sul cammino critico (CP).

    Le attività vengono ordinate nella lista in modo non
    decrescente in base al loro slack, calcolato come:
        Slack_j = LF_j - EF_j
    Le attività con valori di slack alti sono meno urgenti
    e più flessibili, quelle con valori si slack bassi o
    prossimi allo zero hanno una priorità alta e quindi sono
    task critici. Se lo slack è negativo l'attività j è 
    in ritardo.

    Restituisce:
        - priority_list = [j_1, j_2, ....]
    """
    # Costruzione grafo
    succs = {i: [] for i in range(n)}
    preds = {i: [] for i in range(n)}

    for i, j, min_lag, _ in precedences:
        succs[i].append((j, min_lag))
        preds[j].append((i, min_lag))

    # Forward pass per EST (Earliest Starting Time)
    EST = [0] * n

    changed = True
    while changed:
        changed = False
        for j in range(n):
            for i, min_lag in preds[j]:
                val = EST[i] + min_lag
                if EST[j] < val:
                    EST[j] = val
                    changed = True

    # Backward pass per LFT (Latest Finishing Time)
    LST = [horizon] * n
    last = n - 1
    LST[last] = horizon

    changed = True
    while changed:
        changed = False
        for i in range(n):
            for j, min_lag in succs[i]:
                val = LST[j] - min_lag
                if LST[i] > val:
                    LST[i] = val
                    changed = True

    # Calcolo Slack
    SLK = [LST[i] - EST[i] for i in range(n)]

    return sorted(range(n), key=lambda x: SLK[x])