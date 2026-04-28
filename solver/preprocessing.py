from utils.validators.validate_input_rcpsp import validate_inputs as val_inputs_rcpsp
from utils.validators.validate_input_rcpsp_max import validate_inputs as val_inputs_rcpsp_max

#————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
# PREPROCESSING DEGLI INPUT PER COMPATIBILITÀ MODELLI
#————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————

def _pre_processing_rcpsp(orch, n: int, durations: list[int], precedences: list[tuple[int,int]], resources: list[int], 
                            consumption: list[list[int]], horizon: int):
    """
    Preprocessing dei dati di input per il problema RCPSP.
    
    Trasforma i dati forniti dall'utente nel formato interno richiesto dal modello.
    Aggiunge le attività dummy iniziale e finale, effettua lo shift degli indici
    per adattarsi alla numerazione interna, e valida i dati processati.
    
    Args:
        n: Numero di attività (senza dummy)
        durations: Lista delle durate di ciascuna attività
        precedences: Lista di tuple (i,j) che rappresentano le precedenze
        resources: Lista delle disponibilità di ciascuna risorsa
        consumption: Matrice dei consumi di risorse per attività
        horizon: Limite temporale per il completamento del progetto
        
    Raises:
        RuntimeError: Se le precedenze hanno un formato errato
        Exception: Se la validazione dei dati fallisce
    """
    for elem in precedences:
        if len(elem) != 2:
            raise RuntimeError("Le precedenze passate hanno un formato errato!")
    
    # Aggiungo le attività dummy, quella iniziale e finale
    orch._n = n + 2
    orch._activities = list(range(orch._n))
    orch._durations = [0] + durations + [0]
    orch._resources = resources
    lista_consumi = [0] * len(orch._resources)
    orch._consumption = [lista_consumi.copy()] + consumption + [lista_consumi.copy()]
    orch._horizon = horizon
    precedences = _shift_precedences(precedences, rcpsp_max=False)
    precedences = _add_dummy_activities(orch, precedences=precedences, rcpsp_max=False)
    orch._precedences = precedences

    # Lancio una validazione dei dati processati
    try:
        val_inputs_rcpsp(orch)
    except Exception as e:
        raise e

def _pre_processing_rcpsp_max(orch,  n: int, durations: list[int], precedences: list[tuple[int,int,str,int,int | None]], resources: list[int], 
                                consumption: list[list[int]], horizon: int, release_dates: list[int], due_dates: list[int]):
    """
    Preprocessing dei dati di input per il problema RCPSP_MAX.
    
    Estende il preprocessing RCPSP per gestire vincoli aggiuntivi come date di inizio
    e scadenza, e precedenze di tipo minmax (FS, SS, FF, SF) con lag minimo e massimo.
    
    Args:
        n: Numero di attività (senza dummy)
        durations: Lista delle durate di ciascuna attività
        precedences: Lista di tuple (i,j,tipo,lag,lag_max) dove tipo è uno tra FS,SS,FF,SF
        resources: Lista delle disponibilità di ciascuna risorsa
        consumption: Matrice dei consumi di risorse per attività
        horizon: Limite temporale per il completamento del progetto
        release_dates: Data di disponibilità di ciascuna attività
        due_dates: Data di scadenza di ciascuna attività
        
    Raises:
        RuntimeError: Se le precedenze hanno un formato errato
        Exception: Se la validazione dei dati fallisce
    """
    for elem in precedences:
        if len(elem) != 5:
            raise RuntimeError("Le precedenze passate hanno un formato errato!")
    
    # Aggiungo le attività dummy, quella iniziale e finale
    orch._n = n + 2
    orch._activities = list(range(orch._n))
    orch._durations = [0] + durations + [0]
    orch._resources = resources
    lista_consumi = [0] * len(orch._resources)
    orch._consumption = [lista_consumi.copy()] + consumption + [lista_consumi.copy()]
    orch._horizon = horizon
    orch._release_dates = [None] + release_dates + [None]
    orch._due_dates = [None] + due_dates + [None]
    precedences = _shift_precedences(precedences, rcpsp_max=True)
    precedences = _convert_precedences_to_minmax(precedences, orch._durations)
    precedences = _add_dummy_activities(orch, precedences=precedences, rcpsp_max=True)
    orch._precedences = precedences

    # Lancio una validazione dei dati processati
    try:
        val_inputs_rcpsp_max(orch)
    except Exception as e:
        raise e

def _convert_precedences_to_minmax(precedences, durations) -> list[tuple[int, int, int, int | None]]:
    """
    Converte le precedenze da formato testuale (FS,SS,FF,SF) al formato interno minmax.
    
    Trasforma le precedenze notazionali standard (FinishStart, StartStart, FinishFinish, StartFinish)
    in vincoli minmax (lag_min, lag_max) utilizzando le durate delle attività.
    Questo è necessario per convertire i vincoli logici in vincoli temporali numerici.
    
    Args:
        precedences: Lista di tuple (i,j,tipo,lag,lag_max)
        durations: Lista delle durate delle attività (per il calcolo dei lag)
        
    Returns:
        Lista di tuple (i, j, lag_minimo, lag_massimo)
        
    Raises:
        ValueError: Se il tipo di precedenza non è supportato
    """
    result = []

    for (i, j, type, lag, max_lag) in precedences:

        if type == "FS":
            min_lag = durations[i] + lag
            max_lag_conv = durations[i] + max_lag if max_lag is not None else None

        elif type == "SS":
            min_lag = lag
            max_lag_conv = max_lag

        elif type == "FF":
            min_lag = durations[i] - durations[j] + lag
            max_lag_conv = durations[i] - durations[j] + max_lag if max_lag is not None else None

        elif type == "SF":
            min_lag = -durations[j] + lag
            max_lag_conv = -durations[j] + max_lag if max_lag is not None else None

        else:
            raise ValueError(f"Tipo precedenza non supportato: {type}")

        result.append((i, j, min_lag, max_lag_conv))

    return result

def _add_dummy_activities(orch, precedences, rcpsp_max: bool):
    """
    Aggiunge le attività dummy (inizio e fine) al grafo delle precedenze.
    
    Le attività dummy sono necessarie per rappresentare il punto di inizio e il punto di fine
    di tutto il progetto. Connette tutte le attività senza predecessori alla dummy iniziale
    e tutte le attività senza successori alla dummy finale.
    Questo garantisce una struttura di grafo valida per gli algoritmi di scheduling.
    
    Args:
        precedences: Lista delle precedenze (già shiftate)
        rcpsp_max: True se il problema è RCPSP_MAX, False se RCPSP
        
    Returns:
        Lista aggiornata delle precedenze con i collegamenti alle dummy aggiunti
    """
    new_precedences = []

    has_pred = dict.fromkeys(range(orch._n), False)
    has_succ = dict.fromkeys(range(orch._n), False)

    if rcpsp_max: 
        for (i, j, min_lag, max_lag) in precedences:
            has_pred[j] = True
            has_succ[i] = True

        # dummy start = 0
        for j in range(1, orch._n - 1):
            if not has_pred[j]:
                new_precedences.append((0, j, 0, None))

        # dummy end = n-1
        for i in range(1, orch._n - 1):
            if not has_succ[i]:
                new_precedences.append((i, orch._n - 1, orch._durations[i], None))
    else:
        for (i, j) in precedences:
            has_pred[j] = True
            has_succ[i] = True

        # dummy start = 0
        for j in range(1, orch._n - 1):
            if not has_pred[j]:
                new_precedences.append((0, j))

        # dummy end = n-1
        for i in range(1, orch._n - 1):
            if not has_succ[i]:
                new_precedences.append((i, orch._n - 1))

    return precedences + new_precedences

def _shift_precedences(precedences, rcpsp_max: bool):
    """
    Effettua lo shift degli indici delle precedenze di +1.
    
    Questa operazione è necessaria perché l'utente fornisce attività numerati da 0,
    ma internamente la dummy iniziale occupa l'indice 0. Pertanto tutti gli indici
    delle attività devono essere shiftati di +1.
    
    Args:
        precedences: Lista delle precedenze originali (numerazione utente 0-based)
        rcpsp_max: True se il problema è RCPSP_MAX, False se RCPSP
        
    Returns:
        Lista delle precedenze con indici shiftati di +1
    """
    shifted = []

    if rcpsp_max:
        for p in precedences:
            i, j = p[0], p[1]
            rest = p[2:]

            shifted.append((i+1, j+1, *rest))
    else:
        for p in precedences:
            i, j = p[0], p[1]

            shifted.append((i+1, j+1))

    return shifted