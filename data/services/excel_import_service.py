"""
Modulo per l'importazione dei dati di un'istanza dei problemi RCPSP e RCPSP/MAX 
dal file Excel input_data.xlsx.

Struttura del file Excel input_data.xlsx:
- Foglio 'Attività a Risorse':
        ID Attività | Nome Attività | Durata Minima | Durata Massima (Opzionale) | Risorsa 1 | Risorsa 2 | ...
                                                                                       30          20
              1           Task 1            6                                           0           8
              2           Task 2            8                                           0           12
              3           Task 3            4                     7                     10          0

- Foglio 'Date e Scadenze':
        ID Attività | Nome Attività | Data di Rilascio Minima | Data di Rilascio Massima | Data Scadenza Minima | Data Scadenza Massima
        1            Task 1           11/05/2026                                           30/05/2026             
        2            Task 2           15/05/2026                20/05/2026                 
        3            Task 3                                                                12/06/2026

- Foglio 'Legami e Precedenze':
        Attività Precedente | Attività Successiva | Tipo di Legame  | Distanza Minima (Lag temporale) | Distanza Massima (Opzionale)
        Task 2                Task 4                Inizio -> Inizio  5                                 6
        Task 7                Task 8                Fine -> Inizio                            
            
"""

from solver.dataclasses.input_data import InputData
import pandas as pd
from utils.converter.calendar_utils import convert_datetime_to_working_days
from datetime import datetime
from typing import List

class ExcelImportService:
    """
    Importa i dati da un file Excel e li converte in InputData.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._idMapTask = {}

    def _get_data_frame(self, sheet_name: str) -> pd.DataFrame:
        try:
            df = pd.read_excel(self.file_path, sheet_name=sheet_name)
            return df
        except FileNotFoundError:
            raise FileNotFoundError(f"Il file {self.file_path} non esiste.")
        except Exception as e:
            raise Exception(f"Errore durante la lettura del file: {e}")

    def _extract_activities_data(self, df: pd.DataFrame) -> List[dict]:
        id_activities = df["ID Attività"].dropna().astype(int).tolist()
        names = df["Nome Attività"].dropna().tolist()
        durations = df["Durata Minima"].dropna().astype(int).tolist()
        durations_max = df["Durata Massima (Opzionale)"].tolist()
        durations_max = durations_max[1:]
        durations_max = [int(d) if not pd.isna(d) else durations[i] for i, d in enumerate(durations_max)]
        list_activities = []
        for i, id in enumerate(id_activities):
            self._idMapTask[names[i]] = id
            list_activities.append({
                "id": id,
                "name": names[i],
                "duration": durations[i],
                "duration_max": durations_max[i]
            })
        return list_activities

    def _extract_resources_data(self, df: pd.DataFrame):
        list_resources_data = []
        for colonna in df.columns[4:]:
            dati = df[colonna].dropna().tolist()
            if not dati:
                continue
            cap_max = dati[0]
            consumption_ris = [int(x) for x in dati[1:]]
            if '-' in str(cap_max):
                ris_min, ris_max = cap_max.split('-')
                cap_max = (int(ris_min.strip()), int(ris_max.strip()))
            else:
                cap_max = int(cap_max)
            list_resources_data.append({
                "name": colonna,
                "capacity": cap_max,
                "consumption": consumption_ris
            })
        return list_resources_data
    
    def _extract_release_dates_data(self, df: pd.DataFrame, start_date: datetime):
        id_activities = df["ID Attività"].dropna().astype(int).tolist()
        names = df["Nome Attività"].dropna().tolist()
        release_dates_min = df["Data di Rilascio Minima"].tolist()
        release_dates_max = df["Data di Rilascio Massima"].tolist()
        release_dates_min = [convert_datetime_to_working_days(start_date, pd.to_datetime(date, dayfirst=True)) if pd.notna(date) else None for date in release_dates_min]
        release_dates_max = [convert_datetime_to_working_days(start_date, pd.to_datetime(date, dayfirst=True)) if pd.notna(date) else None for date in release_dates_max]
        list_release_dates_data = []
        for i, id in enumerate(id_activities):
            list_release_dates_data.append({
                "id": id,
                "name": names[i],
                "release_date_min": release_dates_min[i],
                "release_date_max": release_dates_max[i]
            })
        return list_release_dates_data
        
    def _extract_due_dates_data(self, df: pd.DataFrame, start_date: datetime):
        id_activities = df["ID Attività"].dropna().astype(int).tolist()
        names = df["Nome Attività"].dropna().tolist()
        due_dates_min = df["Data di Scadenza Minima"].tolist()
        due_dates_max = df["Data di Scadenza Massima"].tolist()
        due_dates_min = [convert_datetime_to_working_days(start_date, pd.to_datetime(date, dayfirst=True)) if pd.notna(date) else None for date in due_dates_min]
        due_dates_max = [convert_datetime_to_working_days(start_date, pd.to_datetime(date, dayfirst=True)) if pd.notna(date) else None for date in due_dates_max]
        list_due_dates_data = []
        for i, id in enumerate(id_activities):
            list_due_dates_data.append({
                "id": id,
                "name": names[i],
                "due_date_min": due_dates_min[i],
                "due_date_max": due_dates_max[i]
            })
        return list_due_dates_data
    
    def _extract_precedences_data(self, df: pd.DataFrame):
        predecessor_activities = df["Attività Precedente"].dropna().tolist()
        successor_activities = df["Attività Successiva"].dropna().tolist()
        link_types = df["Tipo di Legame"].dropna().tolist()
        lag_times = df["Distanza Minima (Lag temporale)"].tolist()
        lag_times_max = df["Distanza Massima (Opzionale)"].tolist()
        lag_times = [int(l) if not pd.isna(l) else 0 for l in lag_times]
        lag_times_max = [int(l) if not pd.isna(l) else 0 for l in lag_times_max]
        list_precedences_data = []
        link_types = list(map(lambda x: x.replace("Fine -> Inizio (Standard)", "FS").replace("Fine -> Fine", "FF").replace("Inizio -> Inizio", "SS").replace("Inizio -> Fine", "SF"), link_types))
        for i, predecessor_activity in enumerate(predecessor_activities):
            list_precedences_data.append({
                "predecessor_activity": predecessor_activity,
                "successor_activity": successor_activities[i],
                "link_type": link_types[i],
                "lag_time": lag_times[i],
                "lag_time_max": lag_times_max[i] if lag_times_max[i] != 0 else None
            })
        return list_precedences_data

    def _check_activities_consistency(self, list_activities_data: List[dict], list_precedences_data: List[dict], list_release_dates_data: List[dict], list_due_dates_data: List[dict], list_resources_data: List[dict]):
        """
        Verifica la coerenza dei dati importati dal file Excel.
        Lancia ValueError in caso di inconsistenze.
        """

        # =========================
        # ATTIVITÀ
        # =========================

        ids = [a["id"] for a in list_activities_data]
        names = [a["name"] for a in list_activities_data]

        # ID univoci
        if len(ids) != len(set(ids)):
            raise ValueError("Sono presenti ID attività duplicati.")

        # Nomi univoci
        if len(names) != len(set(names)):
            raise ValueError("Sono presenti nomi attività duplicati.")

        # Durate coerenti
        for activity in list_activities_data:

            if activity["duration"] <= 0:
                raise ValueError(
                    f"L'attività '{activity['name']}' ha una durata minima non valida."
                )

            if activity["duration_max"] < activity["duration"]:
                raise ValueError(
                    f"L'attività '{activity['name']}' ha una durata massima "
                    f"minore della durata minima."
                )

        # Dizionari utili per confronti rapidi
        id_to_name = {a["id"]: a["name"] for a in list_activities_data}
        valid_names = set(names)

        # =========================
        # RELEASE DATES
        # =========================

        for release in list_release_dates_data:

            activity_id = release["id"]
            activity_name = release["name"]

            # ID esistente
            if activity_id not in id_to_name:
                raise ValueError(
                    f"L'attività ID={activity_id} nel foglio "
                    f"'Date e Scadenze' non esiste."
                )

            # Nome coerente con ID
            if id_to_name[activity_id] != activity_name:
                raise ValueError(
                    f"Incoerenza tra ID e nome attività "
                    f"nel foglio 'Date e Scadenze': "
                    f"ID={activity_id}, Nome='{activity_name}'."
                )

            release_min = release["release_date_min"]
            release_max = release["release_date_max"]

            # Max senza Min
            if release_min is None and release_max is not None:
                raise ValueError(
                    f"L'attività '{activity_name}' ha una release max "
                    f"ma non una release min."
                )

            # Coerenza min/max
            if (
                release_min is not None and
                release_max is not None and
                release_max < release_min
            ):
                raise ValueError(
                    f"L'attività '{activity_name}' ha release max "
                    f"minore della release min."
                )

        # =========================
        # DUE DATES
        # =========================

        for due in list_due_dates_data:

            activity_id = due["id"]
            activity_name = due["name"]

            # ID esistente
            if activity_id not in id_to_name:
                raise ValueError(
                    f"L'attività ID={activity_id} nel foglio "
                    f"'Date e Scadenze' non esiste."
                )

            # Nome coerente
            if id_to_name[activity_id] != activity_name:
                raise ValueError(
                    f"Incoerenza tra ID e nome attività "
                    f"nel foglio 'Date e Scadenze': "
                    f"ID={activity_id}, Nome='{activity_name}'."
                )

            due_min = due["due_date_min"]
            due_max = due["due_date_max"]

            # Max senza Min
            if due_min is None and due_max is not None:
                raise ValueError(
                    f"L'attività '{activity_name}' ha una due date max "
                    f"ma non una due date min."
                )

            # Coerenza min/max
            if (
                due_min is not None and
                due_max is not None and
                due_max < due_min
            ):
                raise ValueError(
                    f"L'attività '{activity_name}' ha una due date max "
                    f"minore della due date min."
                )

        # =========================
        # RELEASE VS DUE DATE
        # =========================

        due_map = {
            d["id"]: d
            for d in list_due_dates_data
        }

        for release in list_release_dates_data:

            activity_id = release["id"]
            activity_name = release["name"]

            release_min = release["release_date_min"]
            release_max = release["release_date_max"]

            due = due_map.get(activity_id)

            if due is None:
                continue

            due_min = due["due_date_min"]
            due_max = due["due_date_max"]

            # release min > due min
            if (
                release_min is not None and
                due_min is not None and
                release_min > due_min
            ):
                raise ValueError(
                    f"L'attività '{activity_name}' ha "
                    f"release min maggiore della due min."
                )

            # release max > due max
            if (
                release_max is not None and
                due_max is not None and
                release_max > due_max
            ):
                raise ValueError(
                    f"L'attività '{activity_name}' ha "
                    f"release max maggiore della due max."
                )

        # =========================
        # PRECEDENZE
        # =========================

        valid_link_types = {"FS", "FF", "SS", "SF"}

        for precedence in list_precedences_data:

            predecessor = precedence["predecessor_activity"]
            successor = precedence["successor_activity"]

            # Task esistenti
            if predecessor not in valid_names:
                raise ValueError(
                    f"L'attività predecessore '{predecessor}' non esiste."
                )

            if successor not in valid_names:
                raise ValueError(
                    f"L'attività successiva '{successor}' non esiste."
                )

            # Nessun autolegame
            if predecessor == successor:
                raise ValueError(
                    f"L'attività '{predecessor}' non può dipendere da sé stessa."
                )

            # Tipo legame valido
            if precedence["link_type"] not in valid_link_types:
                raise ValueError(
                    f"Tipo di legame non valido tra "
                    f"'{predecessor}' e '{successor}'."
                )

            lag = precedence["lag_time"]
            lag_max = precedence["lag_time_max"]

            # Lag coerenti
            if lag_max is not None and lag_max < lag:
                raise ValueError(
                    f"Il lag massimo tra '{predecessor}' "
                    f"e '{successor}' è minore del lag minimo."
                )

        # =========================
        # RISORSE
        # =========================

        num_activities = len(list_activities_data)

        for resource in list_resources_data:

            name = resource["name"]
            capacity = resource["capacity"]
            consumptions = resource["consumption"]

            # Capacità valida
            if isinstance(capacity, int) and capacity < 0:
                raise ValueError(
                    f"La risorsa '{name}' ha capacità negativa."
                )
            elif isinstance(capacity, tuple):
                cap_min, cap_max = resource["capacity"]
                if cap_min < 0 or cap_max < 0:
                    raise ValueError(
                        f"La risorsa '{name}' ha capacità negativa."
                    )
                if cap_max < cap_min:
                    raise ValueError(
                        f"La risorsa '{name}' ha capacità massima minore della capacità minima."
                    )

            # Numero consumi coerente
            if len(consumptions) != num_activities:
                raise ValueError(
                    f"La risorsa '{name}' non ha un numero "
                    f"corretto di consumi."
                )

            for consumption in consumptions:

                # Consumo valido
                if consumption < 0:
                    raise ValueError(
                        f"La risorsa '{name}' contiene consumi negativi."
                    )

                # Consumo > capacità
                if isinstance(capacity, int) and consumption > capacity:
                    raise ValueError(
                        f"La risorsa '{name}' contiene un consumo "
                        f"maggiore della capacità."
                    )
                elif isinstance(capacity, tuple) and consumption > capacity[1]:
                    raise ValueError(
                        f"La risorsa '{name}' contiene un consumo "
                        f"maggiore della capacità."
                    )

    def load_instance_from_excel(self, start_date_project: datetime, end_date_project: datetime) -> InputData:
        """
        Carica i dati dal file Excel, esegue dei controlli minimi e restituisce 
        un oggetto InputData.
        """
        df_attivita_risorse = self._get_data_frame("Attività e Risorse")
        df_date_scadenze = self._get_data_frame("Date e Scadenze")
        df_legami_precedenze = self._get_data_frame("Legami e Precedenze")
        list_activities_data = self._extract_activities_data(df_attivita_risorse)
        list_resources_data = self._extract_resources_data(df_attivita_risorse)
        list_release_dates_data = self._extract_release_dates_data(df_date_scadenze, start_date_project)
        list_due_dates_data = self._extract_due_dates_data(df_date_scadenze, start_date_project)
        list_precedences_data = self._extract_precedences_data(df_legami_precedenze)

        self._check_activities_consistency(list_activities_data, list_precedences_data, list_release_dates_data, list_due_dates_data, list_resources_data)

        list_ids = [x.get("id") for x in list_activities_data]
        n = len(list_ids)
        horizon = convert_datetime_to_working_days(start_date_project, end_date_project)
        list_durations = [x.get("duration") if x.get("duration") == x.get("duration_max") else (x.get("duration"), x.get("duration_max")) for x in list_activities_data]
        list_activities_names = [x.get("name") for x in list_activities_data]
        list_resources_names = [x.get("name") for x in list_resources_data]
        list_resources_capacities = [x.get("capacity") for x in list_resources_data]
        list_release_dates = [x.get("release_date_min") if x.get("release_date_max") is None else (x.get("release_date_min"), x.get("release_date_max")) for x in list_release_dates_data]
        list_due_dates = [x.get("due_date_min") if x.get("due_date_max") is None else (x.get("due_date_min"), x.get("due_date_max")) for x in list_due_dates_data]
        rcpsp_max = False
        for x in list_precedences_data:
            if x.get("lag_time_max") is not None:
                rcpsp_max = True
                break
        if rcpsp_max:
            list_precedences = [(self._idMapTask.get(x.get("predecessor_activity")), self._idMapTask.get(x.get("successor_activity")), x.get("link_type"), x.get("lag_time"), x.get("lag_time_max")) if x.get("lag_time") is not None else (self._idMapTask.get(x.get("predecessor_activity")), self._idMapTask.get(x.get("successor_activity")), x.get("link_type"), 0, x.get("lag_time_max")) for x in list_precedences_data]
        else:
            list_precedences = [(self._idMapTask.get(x.get("predecessor_activity")), self._idMapTask.get(x.get("successor_activity"))) for x in list_precedences_data]
        list_consumption = []
        for i, act in enumerate(list_activities_data):
            list_cons_act = []
            for ris in list_resources_data:
                consumption = ris.get("consumption")[i]
                list_cons_act.append(consumption)
            list_consumption.append(list_cons_act)

        has_intervals = any(isinstance(x, tuple) for x in list_durations) or any(isinstance(x, tuple) for x in list_release_dates) or any(isinstance(x, tuple) for x in list_due_dates or any(isinstance(x, tuple) for x in list_resources_capacities))
        
        input_data = InputData(
            n=n,
            horizon=horizon,
            durations=list_durations,
            precedences=list_precedences,
            resources=list_resources_capacities,
            release_dates=list_release_dates,
            due_dates=list_due_dates,
            consumption=list_consumption,
            activity_names=list_activities_names,
            resource_names=list_resources_names,
            rcpsp_max=rcpsp_max,
            has_intervals=has_intervals,
        )
        from pprint import pprint
        pprint(input_data.model_dump())
        return input_data
        
if __name__ == "__main__":
    ex_import_service = ExcelImportService("data/files/input_data.xlsx")
    ex_import_service.load_instance_from_excel(datetime(2026, 5, 12), datetime(2027, 4, 11))