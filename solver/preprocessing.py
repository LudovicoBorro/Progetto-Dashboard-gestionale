from utils.validators.validate_input_rcpsp import validate_inputs as val_inputs_rcpsp
from utils.validators.validate_input_rcpsp_max import validate_inputs as val_inputs_rcpsp_max
from pydantic import BaseModel

#————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
# PREPROCESSING DEGLI INPUT PER COMPATIBILITÀ MODELLI
#————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————

class ProcessedRCPSPMax(BaseModel):
    n: int
    activities: list[int]
    durations: list[int]
    precedences: list[tuple[int, int, int, int | None]]
    resources: list[int]
    consumption: list[list[int]]
    horizon: int
    release_dates: list[int | None]
    due_dates: list[int | None]

class ProcessedRCPSP(BaseModel):
    n: int
    activities: list[int]
    durations: list[int]
    precedences: list[tuple[int, int]]
    resources: list[int]
    consumption: list[list[int]]
    horizon: int

def _pre_processing_rcpsp(n: int, durations: list[int], precedences: list[tuple[int,int]], resources: list[int], 
                            consumption: list[list[int]], horizon: int) -> ProcessedRCPSP:
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
    new_n = n + 2
    activities = list(range(new_n))
    new_durations = [0] + durations + [0]
    lista_consumi = [0] * len(resources)
    new_consumption = [lista_consumi.copy()] + consumption + [lista_consumi.copy()]
    precedences = _shift_precedences(precedences, rcpsp_max=False)
    precedences = _add_dummy_activities(n=new_n, durations=new_durations, precedences=precedences, rcpsp_max=False)

    processed = ProcessedRCPSP(
        n=new_n,
        activities=activities,
        durations=new_durations,
        precedences=precedences,
        resources=resources,
        consumption=new_consumption,
        horizon=horizon
    )

    # Lancio una validazione dei dati processati
    val_inputs_rcpsp(processed)

def _pre_processing_rcpsp_max(
    n: int,
    durations: list[int],
    precedences: list[tuple[int, int, int, int | None]],
    resources: list[int],
    consumption: list[list[int]],
    horizon: int,
    release_dates: list[int | None],
    due_dates: list[int | None]
) -> ProcessedRCPSPMax:

    # -------- VALIDAZIONE BASE --------
    for elem in precedences:
        if len(elem) != 5:
            raise RuntimeError("Formato precedenze errato")

    # -------- COSTRUZIONE DATI --------
    new_n = n + 2
    activities = list(range(new_n))

    new_durations = [0] + durations + [0]

    zero_cons = [0] * len(resources)
    new_consumption = [zero_cons.copy()] + consumption + [zero_cons.copy()]

    new_release = [None] + release_dates + [None]
    new_due = [None] + due_dates + [None]

    # -------- PRECEDENZE --------
    precedences = _shift_precedences(precedences, rcpsp_max=True)
    precedences = _convert_precedences_to_minmax(precedences, new_durations)
    precedences = _add_dummy_activities(
        n=new_n,
        durations=new_durations,
        precedences=precedences,
        rcpsp_max=True
    )

    processed = ProcessedRCPSPMax(
        n=new_n,
        activities=activities,
        durations=new_durations,
        precedences=precedences,
        resources=resources,
        consumption=new_consumption,
        horizon=horizon,
        release_dates=new_release,
        due_dates=new_due
    )

    # -------- VALIDAZIONE --------
    val_inputs_rcpsp_max(processed)

    return processed

def _add_dummy_activities(n, durations, precedences, rcpsp_max: bool):

    new_precedences = []

    has_pred = dict.fromkeys(range(n), False)
    has_succ = dict.fromkeys(range(n), False)

    if rcpsp_max:
        for (i, j, min_lag, max_lag) in precedences:
            has_pred[j] = True
            has_succ[i] = True

        # dummy start = 0
        for j in range(1, n - 1):
            if not has_pred[j]:
                new_precedences.append((0, j, 0, None))

        # dummy end = n-1
        for i in range(1, n - 1):
            if not has_succ[i]:
                new_precedences.append((i, n - 1, durations[i], None))

    else:
        for (i, j) in precedences:
            has_pred[j] = True
            has_succ[i] = True

        # dummy start = 0
        for j in range(1, n - 1):
            if not has_pred[j]:
                new_precedences.append((0, j))

        # dummy end = n-1
        for i in range(1, n - 1):
            if not has_succ[i]:
                new_precedences.append((i, n - 1))

    return precedences + new_precedences

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