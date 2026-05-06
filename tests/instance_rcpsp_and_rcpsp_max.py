import random

class Instance: 
    
    def __init__(self):
        raise RuntimeError("Attenzione! Non creare un'istanza di questa classe! Richiama la funzione statica get_instance()!")

    @staticmethod
    def get_instance():
        n = 30
        activities = list(range(n))

        durations = [
            0,
            5, 3, 7, 2, 6, 4, 8, 3, 5,
            9, 2, 6, 4, 7, 3, 5, 8, 6, 2,
            7, 4, 3, 9, 5, 6, 2, 8, 4,
            0
        ]

        resources = [15, 12, 10]

        precedences_rcpsp = [
            (0,1),(0,2),(0,3),

            (1,4),(1,5),
            (2,6),(2,7),
            (3,8),(3,9),

            (4,10),(5,10),
            (5,11),
            (6,11),(7,12),
            (8,12),(9,13),

            (10,14),(11,15),(12,16),(13,17),

            (14,18),(15,18),
            (15,19),(16,19),
            (17,20),

            (18,21),(19,22),(20,23),

            (21,24),(22,25),(23,26),

            (24,27),(25,27),(26,28),

            (27,29),(28,29)
        ]

        # Conversione in RCPSP/Max
        precedences_rcpsp_max = []
        for (i, j) in precedences_rcpsp:
            if random.random() > 0.8:
                max_lag = durations[i] + int(random.random() * durations[i] // 2)
            else:
                max_lag = None
            precedences_rcpsp_max.append((i, j, durations[i], max_lag))

        horizon = sum(durations[i] for i in activities)

        consumption = [
            [0,0,0],
            [3,2,1],[5,3,2],[6,4,2],[2,5,3],[4,2,2],[7,5,3],[6,6,2],[3,4,1],[5,3,2],
            [8,6,3],[2,2,1],[5,4,2],[4,3,2],[6,5,3],[3,3,1],[4,2,2],[7,6,3],[5,4,2],[2,2,1],
            [6,5,3],[4,3,2],[3,2,1],[8,6,3],[5,4,2],[6,5,3],[2,2,1],[7,6,3],[4,3,2],
            [0,0,0]
        ]

        release_dates = [
            None,
            0, None, 3, None, None, 5, None, None, 4,
            None, 6, None, None, 8, None, None, 10, None, None,
            12, None, None, 14, None, None, 16, None, None,
            None
        ]

        due_dates = [
            None,
            None, None, None, 40, 45, None, 42, None, None,
            60, None, 65, None, 70, None, 75, None, 80, None,
            90, None, None, 100, None, 105, None, 110, None,
            None
        ]

        return n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, horizon, consumption, release_dates, due_dates
    
    @staticmethod
    def get_raw_instance():
        n = 28
        activities = list(range(n))

        durations = [
            5, 3, 7, 2, 6, 4, 8, 3, 5,
            9, 2, 6, 4, 7, 3, 5, 8, 6, 2,
            7, 4, 3, 9, 5, 6, 2, 8, 4,
        ]

        resources = [15, 12, 10]

        precedences_rcpsp = [

            (1,4),(1,5),
            (2,6),(2,7),
            (3,8),(3,9),

            (4,10),(5,10),
            (5,11),
            (6,11),(7,12),
            (8,12),(9,13),

            (10,14),(11,15),(12,16),(13,17),

            (14,18),(15,18),
            (15,19),(16,19),
            (17,20),

            (18,21),(19,22),(20,23),

            (21,24),(22,25),(23,26),

            (24,27),(25,27),(26,28),

        ]

        # Conversione in RCPSP/Max
        precedences_rcpsp_max = []
        prec = ["FS", "SS", "SF", "FF"]
        for (i, j) in precedences_rcpsp:
            if random.random() > 0.8:
                max_lag_val = durations[i] + int(random.random() * durations[i] // 2)
            else:
                max_lag_val = None
                
            lag = 2 # Valore minimo per testare RCPSP/Max senza eccedere l'orizzonte
            if max_lag_val is not None:
                # Mantieni lo slack originale rispetto alla durata
                slack = max_lag_val - durations[i]
                max_lag = lag + max(1, slack)
            else:
                max_lag = None
            precedences_rcpsp_max.append((i, j, "FS", lag, max_lag))

        horizon = sum(durations[i] for i in activities)

        consumption = [
            [3,2,1],[5,3,2],[6,4,2],[2,5,3],[4,2,2],[7,5,3],[6,6,2],[3,4,1],[5,3,2],
            [8,6,3],[2,2,1],[5,4,2],[4,3,2],[6,5,3],[3,3,1],[4,2,2],[7,6,3],[5,4,2],[2,2,1],
            [6,5,3],[4,3,2],[3,2,1],[8,6,3],[5,4,2],[6,5,3],[2,2,1],[7,6,3],[4,3,2],
        ]

        release_dates = [
            None, None, 3, None, None, 5, None, None, 4,
            None, 6, None, None, 8, None, None, 10, None, None,
            12, None, None, 14, None, None, 16, None, None,
        ]

        due_dates = [
            None, None, None, 40, 45, None, 42, None, None,
            60, None, 65, None, 70, None, 75, None, 80, None,
            90, None, None, 100, None, 105, None, 110, None,
        ]

        return n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, horizon, consumption, release_dates, due_dates
    

    @staticmethod
    def get_raw_instance_with_intervals():
        n = 28
        activities = list(range(n))

        # 10 tuple
        durations = [
            5, 3, 7, (2,4), 6, (4,9), (5,8), (3,10), 5,
            9, 2, (6,8), 4, 7, 3, (5,9), 8, 6, 2,
            (7,8), 4, 3, (9,15), 5, 6, 2, (8,13), (10,12),
        ]

        # 2 tuple
        resources = [(12,13), 12, (9,11)]

        precedences_rcpsp = [

            (1,4),(1,5),
            (2,6),(2,7),
            (3,8),(3,9),

            (4,10),(5,10),
            (5,11),
            (6,11),(7,12),
            (8,12),(9,13),

            (10,14),(11,15),(12,16),(13,17),

            (14,18),(15,18),
            (15,19),(16,19),
            (17,20),

            (18,21),(19,22),(20,23),

            (21,24),(22,25),(23,26),

            (24,27),(25,27),(26,28),

        ]

        # Conversione in RCPSP/Max
        # Nota: usiamo 'low' (durata minima) come lag FS, così il vincolo
        # start_j >= start_i + dur_i + low è sempre soddisfacibile anche
        # quando il B&B fissa le durate al valore minimo.
        # Il max_lag è garantito > lag (almeno +1) per evitare finestre a zero larghezza.
        precedences_rcpsp_max = []
        for (i,j) in precedences_rcpsp:
            if isinstance(durations[i], tuple):
                low, high = durations[i]
            else:
                low = high = durations[i]
            lag = 2 # Valore minimo per testare RCPSP/Max
            if random.random() > 0.8:
                # Garantisce max_lag > lag con un po' di respiro
                extra = max(2, int(random.random() * (high - low + 2)) + 2)
                max_lag = lag + extra
            else:
                max_lag = None
            precedences_rcpsp_max.append((i,j,"FS",lag,max_lag))

        horizon = 0
        for i in activities:
            if isinstance(durations[i], tuple):
                _, high = durations[i]
            else:
                high = durations[i]
            horizon += high

        consumption = [
            [3,2,1],[5,3,2],[6,4,2],[2,5,3],[4,2,2],[7,5,3],[6,6,2],[3,4,1],[5,3,2],
            [8,6,3],[2,2,1],[5,4,2],[4,3,2],[6,5,3],[3,3,1],[4,2,2],[7,6,3],[5,4,2],[2,2,1],
            [6,5,3],[4,3,2],[3,2,1],[8,6,3],[5,4,2],[6,5,3],[2,2,1],[7,6,3],[4,3,2],
        ]
        
        # 4 tuple
        release_dates = [
            None, None, (3,7), None, None, 5, None, None, 4,
            None, 6, None, None, 8, None, (12,17), 10, None, None,
            12, None, None, (14,15), None, None, (12,16), None, None,
        ]

        # 4 tuple
        due_dates = [
            None, None, None, (30,40), 45, None, 42, None, None,
            60, None, (65,70), None, 70, None, (75,77), None, 80, None,
            90, None, None, 100, None, (100,107), None, 110, None,
        ]

        # Considerando che si brancha solo su LOW e HIGH, le combinazioni totali sono:
        # 2^10 * 2^2 * 2^4 * 2^4 = 2^20 = 1.048.576 combinazioni

        return n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, horizon, consumption, release_dates, due_dates
    
    @staticmethod
    def get_raw_instance_with_intervals_minimal():
        n = 5
        activities = list(range(n))

        # Intervalli: attività 2 e 4 (2^2)
        durations = [ 
            3,          # 1
            (2, 5),     # 2 (Intervallo)
            4,          # 3
            (3, 6),     # 4 (Intervallo)
            2           # 5
        ]

        # Risorsa fissa
        resources = [(10,12), 10, 10]

        # Precedenze lineari: 1 -> 2 -> 3 -> 4 -> 5
        precedences_rcpsp = [
            (1, 2), (2, 3), (3, 4), (4, 5)
        ]

        # Conversione in RCPSP/Max (logica originale)
        precedences_rcpsp_max = []
        for (i, j) in precedences_rcpsp:
            # Prendi il valore alto della durata per il vincolo FS
            if isinstance(durations[i], tuple):
                _, high = durations[i]
            else:
                high = durations[i]
            
            # Semplificato per il test: max_lag rimosso o minimo
            max_lag = None
            precedences_rcpsp_max.append((i, j, "FS", high, max_lag))

        # Orizzonte calcolato
        horizon = 9
        for i in activities:
            if isinstance(durations[i], tuple):
                _, high = durations[i]
            else:
                high = durations[i]
            horizon += high

        # Consumi (indice 0 ignorato)
        consumption = [
            [2, 1, 1], [3, 2, 1], [2, 1, 2], [4, 2, 1], [2, 1, 1]
        ]
        
        # Release Dates: 1 intervallo su attività 1 (2^1)
        release_dates = [
            None,
            (3, 5), None, None, None
        ]

        # Due Dates: 1 intervallo su attività 5 (2^1)
        due_dates = [
            None, None, None, None, (20, 30)
        ]

        # TOTALE COMBINAZIONI: 2^2 (durate) * 2^1 (release) * 2^1 (due) = 16
        return n, activities, durations, resources, precedences_rcpsp, precedences_rcpsp_max, horizon, consumption, release_dates, due_dates