from collections import deque
import random

def wrapper_rule(
    regola: str,
    n: int,
    durations: list[int] | None = None,
    precedences_rcpsp: list[tuple[int,int]] | None = None,
    precedences_rcpsp_max: list[tuple[int,int,int,int|None]] | None = None,
    resources: list[int] | None = None,
    consumption: list[list[int]] | None = None,
    horizon: int | None = None
):
    if n is None or n <= 0:
        raise ValueError("Inserire un numero di attività valido!")

    regola = regola.lower()
    real_activities = remove_dummy(n)

    real_precedences_rcpsp = None
    real_precedences_rcpsp_max = None

    if precedences_rcpsp is not None:
        real_precedences_rcpsp = remove_dummy_arcs(precedences_rcpsp, 0, n-1)

    if precedences_rcpsp_max is not None:
        real_precedences_rcpsp_max = remove_dummy_arcs_max(precedences_rcpsp_max, 0, n-1)

    # --- SPT ---
    if regola == "spt":
        if durations is None or len(durations) != n:
            raise ValueError("Durate non valide!")
        return spt_list(real_activities, durations)

    # --- MTS ---
    elif regola == "mts":
        if real_precedences_rcpsp is None:
            raise ValueError("Precedenze non valide!")
        return mts_list(real_activities, real_precedences_rcpsp)

    # --- GRD ---
    elif regola == "grd":
        if consumption is None or resources is None:
            raise ValueError("Consumption o resources non validi!")
        return grd_list(real_activities, consumption, resources)

    # --- CP BASED ---
    elif regola in ["lft_rcpsp", "lst_rcpsp", "mslk_rcpsp"]:
        if durations is None or len(durations) != n:
            raise ValueError("Durate non valide!")
        if real_precedences_rcpsp is None:
            raise ValueError("Precedenze non valide!")
        if horizon is None:
            raise ValueError("Horizon non valido!")

        if regola == "lft_rcpsp":
            return lft_list_rcpsp(real_activities, durations, real_precedences_rcpsp, horizon)
        elif regola == "lst_rcpsp":
            return lst_list_rcpsp(real_activities, durations, real_precedences_rcpsp, horizon)
        else:
            return mslk_list_rcpsp(real_activities, durations, real_precedences_rcpsp, horizon)

    # --- RCPSP/MAX ---
    elif regola in ["lft_rcpsp_max", "lst_rcpsp_max", "mslk_rcpsp_max"]:
        if durations is None or len(durations) != n:
            raise ValueError("Durate non valide!")
        if real_precedences_rcpsp_max is None:
            raise ValueError("Precedenze non valide!")
        if horizon is None:
            raise ValueError("Horizon non valido!")

        if regola == "lft_rcpsp_max":
            return lft_list_rcpsp_max(real_activities, durations, real_precedences_rcpsp_max, horizon)
        elif regola == "lst_rcpsp_max":
            return lst_list_rcpsp_max(real_activities, durations, real_precedences_rcpsp_max, horizon)
        else:
            return mslk_list_rcpsp_max(real_activities, durations, real_precedences_rcpsp_max, horizon)

    else:
        raise ValueError(f"Regola non valida: {regola}")
    

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

def mts_list(activities: list[int], precedences: list[tuple[int, int]]):
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
    succ_map = {i: [] for i in activities}
    indegree = {i: 0 for i in activities}

    for i, j in precedences:
        succ_map[i].append(j)
        indegree[j] += 1

    # topological order
    queue = deque([i for i in activities if indegree[i] == 0])
    topo = []

    while queue:
        u = queue.popleft()
        topo.append(u)
        for v in succ_map[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)

    # DP backward
    succ_sets = {i: set() for i in activities}

    for j in reversed(topo):
        for k in succ_map[j]:
            succ_sets[j].add(k)
            succ_sets[j] |= succ_sets[k]

    return sorted(activities, key=lambda j: len(succ_sets[j]), reverse=True)

def grd_list(activities: list[int], consumption: list[list[int]], resources: list[int]):
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

    GRD = {}

    for j in activities:
        GRD[j] = sum(
            consumption[j][r] / resources[r]
            for r in range(len(resources))
            if resources[r] > 0
        )

    return sorted(activities, key=lambda j: GRD[j], reverse=True)

def lft_list_rcpsp(
        activities: list[int],
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
    succ_map = {i: [] for i in activities}
    indegree = {i: 0 for i in activities}

    for i, j in precedences:
        if i in activities and j in activities:
            succ_map[i].append(j)
            indegree[j] += 1

    # Topological order
    queue = deque([i for i in activities if indegree[i] == 0])
    topo = []

    while queue:
        u = queue.popleft()
        topo.append(u)
        for v in succ_map[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)

    # Backward pass
    LFT = {i: horizon for i in activities}

    for j in reversed(topo):
        if succ_map[j]:
            LFT[j] = min(LFT[k] - durations[k] for k in succ_map[j])

    # Priority list
    return sorted(activities, key=lambda j: LFT[j])

def lft_list_rcpsp_max(
        activities: list[int],
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
    succs = {i: [] for i in activities}
    preds = {i: [] for i in activities}

    # Considero solo il min_lag, poichè Belmann-Ford 
    # divergerebbe molto facilmente se ci sono cicli nel grafo
    for i, j, min_lag, _ in precedences:
        if i in activities and j in activities:
            succs[i].append((j, min_lag))
            preds[j].append((i, min_lag))

    # Utilizzo ordine topologico
    indeg = {i: 0 for i in activities}
    for i in activities:
        for j, _ in succs[i]:
            indeg[j] += 1

    q = deque([i for i in activities if indeg[i] == 0])
    topo = []

    while q:
        u = q.popleft()
        topo.append(u)
        for v, _ in succs[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)

    # Calcolo LST
    LST = {i: horizon for i in activities}

    for i in reversed(topo):
        for j, lag in succs[i]:
            LST[i] = min(LST[i], LST[j] - lag)

    # Calcolo LFT
    LFT = {i: LST[i] + durations[i] for i in activities}

    return sorted(activities, key=lambda j: LFT[j])

def lst_list_rcpsp(
        activities: list[int],
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
    succs = {i: [] for i in activities}
    for i, j in precedences:
        if i in activities and j in activities:
            succs[i].append(j)

    # Inizializzazione LFT
    LFT = {i: horizon for i in activities}

    # Backward pass (CPM)
    changed = True
    while changed:
        changed = False
        for i in activities:
            for j in succs[i]:
                if LFT[i] > LFT[j] - durations[j]:
                    LFT[i] = LFT[j] - durations[j]
                    changed = True

    # Calcolo LST
    LST = {i: LFT[i] - durations[i] for i in activities}

    return sorted(activities, key=lambda x: LST[x])

def lst_list_rcpsp_max(
        activities: list[int],
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
    succs = {i: [] for i in activities}
    for i, j, min_lag, _ in precedences:
        if i in activities and j in activities:
            succs[i].append((j, min_lag))

    # Inizializzazione LST
    LST = {i: horizon for i in activities}

    # Backward pass (tipo CPM ma su start)
    changed = True
    while changed:
        changed = False
        for i in activities:
            for j, min_lag in succs[i]:
                if LST[i] > LST[j] - min_lag:
                    LST[i] = LST[j] - min_lag
                    changed = True

    return sorted(activities, key=lambda x: LST[x])

def mslk_list_rcpsp(
        activities: list[int],
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
    succs = {i: [] for i in activities}
    preds = {i: [] for i in activities}

    for i, j in precedences:
        if i in activities and j in activities:
            succs[i].append(j)
            preds[j].append(i)

    # Forward pass per EST (Earliest Starting Time)
    EST = {i: 0 for i in activities}

    changed = True
    while changed:
        changed = False
        for j in activities:
            for i in preds[j]:
                val = EST[i] + durations[i]
                if EST[j] < val:
                    EST[j] = val
                    changed = True

    # Backward pass per LFT (Latest Finishing Time)
    LFT = {i: horizon for i in activities}

    changed = True
    while changed:
        changed = False
        for i in activities:
            for j in succs[i]:
                val = LFT[j] - durations[j]
                if LFT[i] > val:
                    LFT[i] = val
                    changed = True

    # Calcolo LST (Latest Starting Time)
    LST = {i: LFT[i] - durations[i] for i in activities}

    # Calcolo Slack
    SLK = {i: LST[i] - EST[i] for i in activities}

    return sorted(activities, key=lambda x: SLK[x])

def mslk_list_rcpsp_max(
        activities: list[int],
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
    succs = {i: [] for i in activities}
    preds = {i: [] for i in activities}

    for i, j, min_lag, max_lag in precedences:
        if i in activities and j in activities:
            succs[i].append((j, min_lag, max_lag))
            preds[j].append((i, min_lag, max_lag))

    # Forward pass per EST (Earliest Starting Time)
    EST = {i: 0 for i in activities}

    changed = True
    while changed:
        changed = False
        for j in activities:
            for i, min_lag, _ in preds[j]:
                val = EST[i] + min_lag
                if EST[j] < val:
                    EST[j] = val
                    changed = True

    # Backward pass per LST (Latest Starting Time)
    LST = {i: horizon for i in activities}

    changed = True
    while changed:
        changed = False
        for i in activities:
            for j, min_lag, _ in succs[i]:
                val = LST[j] - min_lag
                if LST[i] > val:
                    LST[i] = val
                    changed = True

    # Calcolo Slack
    SLK = {i: LST[i] - EST[i] for i in activities}

    return sorted(activities, key=lambda x: SLK[x])

def remove_dummy(n):
    real_activities = list(range(1, n-1))
    return real_activities

def remove_dummy_arcs(precedences, dummy_start, dummy_end):
    return [
        (i, j)
        for (i, j) in precedences
        if i != dummy_start and i != dummy_end
        and j != dummy_start and j != dummy_end
    ]

def remove_dummy_arcs_max(precedences, dummy_start, dummy_end):
    return [
        (i, j, min_lag, max_lag)
        for (i, j, min_lag, max_lag) in precedences
        if i != dummy_start and i != dummy_end
        and j != dummy_start and j != dummy_end
    ]

if __name__ == "__main__":
    
    n = 10
    activities = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    durations = [0, 7, 2, 8, 9, 10, 2, 3, 4, 0]
    resources = [16, 14, 8]
    precedences_rcpsp = [(0,1),(0,2),(0,3),(1,4),(1,5),(2,6),(2,7),(3,8),(4,9),(5,9),(6,9),(7,9),(8,9)]
    precedences_rcpsp_max = []
    for (i, j) in precedences_rcpsp:
        if random.random() > 0.70:
            max_lag = durations[i] + int(random.random() * durations[i] // 3)
        else:
            max_lag = None
        precedences_rcpsp_max.append((i, j, durations[i], max_lag))
    horizon = sum(durations[i] for i in activities)
    consumption = [[0,0,0],[2,3,1],[6,3,1],[8,6,3],[0,3,6],[0,0,4],[8,4,2],[10,12,0],[7,0,1],[0,0,0]]

    real_activities= remove_dummy(n)
    real_precedences_rcpsp = remove_dummy_arcs(precedences_rcpsp, 0, n-1)
    real_precedences_rcpsp_max = remove_dummy_arcs_max(precedences_rcpsp_max, 0, n-1)

    print("="*60)
    print("Test regola SPT (Short Process Time)")
    print(f"Sequenza iniziale dei job: {real_activities}")
    print(f"Durate dei singoli job: {durations[1:n-1]}")
    print(f"Soluzione trovata: {spt_list(real_activities, durations)}")
    print("="*60)
    print("Test regola MTS (Most Total Successors)")
    print(mts_list(real_activities, real_precedences_rcpsp))
    print("="*60)
    print("Test regola GRD (Greatest Resource Demand)")
    print(grd_list(real_activities, consumption, resources))
    print("="*60)
    print("Test regola LFT (Latest Finishing Time) per RCPSP classico")
    print(lft_list_rcpsp(real_activities, durations, real_precedences_rcpsp, horizon))
    print("="*60)
    print("Test regola LFT (Latest Finishing Time) per RCPSP/Max")
    print(f"Precedenze utilizzate: {real_precedences_rcpsp_max}")
    print(lft_list_rcpsp_max(real_activities, durations, real_precedences_rcpsp_max, horizon))
    print("="*60)
    print("Test regola LST (Latest Starting Time) per RCPSP classico")
    print(lst_list_rcpsp(real_activities, durations, real_precedences_rcpsp, horizon))
    print("="*60)
    print("Test regola LST (Latest Starting Time) per RCPSP/Max")
    print(f"Precedenze utilizzate: {real_precedences_rcpsp_max}")
    print(lst_list_rcpsp_max(real_activities, durations, real_precedences_rcpsp_max, horizon))
    print("="*60)
    print("Test regola MSLK (Minimum Slack Time) per RCPSP classico")
    print(mslk_list_rcpsp(real_activities, durations, real_precedences_rcpsp, horizon))
    print("="*60)
    print("Test regola MSLK (Minimum Slack Time) per RCPSP/Max")
    print(f"Precedenze utilizzate: {real_precedences_rcpsp_max}")
    print(mslk_list_rcpsp_max(real_activities, durations, real_precedences_rcpsp_max, horizon))
    print("="*60)