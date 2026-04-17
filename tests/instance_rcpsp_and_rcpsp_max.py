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