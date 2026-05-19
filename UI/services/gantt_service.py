from data.repositories.activity_repository import ActivityRepository
import uuid
import pandas as pd
from sqlmodel import select
from data.database import get_session
from data.models import Project, Schedule, ScheduleActivity, Activity, Experiment
from utils.converter.calendar_utils import generate_working_dates

class GanttService:

    @staticmethod
    def get_gantt_dataframe(project_id: uuid.UUID) -> tuple[Project, pd.DataFrame]:
        """
        Interroga il database per ottenere l'ultima schedulazione salvata del progetto
        e la converte in un DataFrame pandas formattato per il GanttChart.
        """
        with get_session() as session:
            # 1. Recupero del progetto
            project = session.get(Project, project_id)
            if not project:
                raise ValueError("Progetto non trovato.")

            # 2. Recupero dell'ultimo esperimento associato al progetto
            exp_stmt = select(Experiment).where(Experiment.project_id == project_id).order_by(Experiment.created_at.desc())
            latest_exp = session.exec(exp_stmt).first()
            if not latest_exp:
                raise ValueError("Nessuna schedulazione eseguita per questo progetto.")

            # 3. Recupero dell'ultimo schedule dell'esperimento
            sch_stmt = select(Schedule).where(Schedule.experiment_id == latest_exp.id).order_by(Schedule.created_at.desc())
            latest_schedule = session.exec(sch_stmt).first()
            if not latest_schedule:
                raise ValueError("Nessuna schedulazione trovata.")

            # 4. Recupero delle attività della schedulazione
            sa_stmt = select(ScheduleActivity).where(ScheduleActivity.schedule_id == latest_schedule.id)
            schedule_activities = session.exec(sa_stmt).all()
            if not schedule_activities:
                raise ValueError("Nessuna attività trovata nella schedulazione.")

            # 5. Estrazione e popolamento dati per il DataFrame
            activities = []
            start_times = []
            activity_durations = []
            end_times = []
            completion_fracs = []
            completion_days_list = []

            max_end_time = 0
            for sa in schedule_activities:
                if sa.end_time > max_end_time:
                    max_end_time = sa.end_time

            # Genera la timeline delle date lavorative
            working_dates = generate_working_dates(
                start_date=project.start_date,
                num_days=max_end_time + 2,
                from_today=False
            )

            start_dates = []
            end_dates = []

            for sa in schedule_activities:
                # Recupera il nome dell'attività reale
                repo = ActivityRepository(session)
                act = repo.get_by_id(sa.activity_id)
                print(f"[DEBUG] Activity id {sa.activity_id}: {act}")   
                act_name = act.name

                activities.append(act_name)
                start_times.append(sa.start_time)
                activity_durations.append(sa.duration)
                end_times.append(sa.end_time)
                completion_fracs.append(sa.actual_progress)
                
                comp_days = sa.actual_progress * sa.duration
                completion_days_list.append(comp_days)

                # Mappatura dei tempi interi (working days) alle date reali
                start_dt = working_dates[sa.start_time] if sa.start_time < len(working_dates) else working_dates[-1]
                end_dt = working_dates[sa.end_time] if sa.end_time < len(working_dates) else working_dates[-1]
                start_dates.append(pd.to_datetime(start_dt))
                end_dates.append(pd.to_datetime(end_dt))

            df = pd.DataFrame({
                "activity": activities,
                "start_time": start_times,
                "activity_duration": activity_durations,
                "end_time": end_times,
                "start_date": start_dates,
                "end_date": end_dates,
                "completion_frac": completion_fracs,
                "completion_days": completion_days_list
            })

            print(f"[DEBUG] DataFrame: {df}")

            # Ordina le attività per tempo di inizio per una resa visiva migliore
            df = df.sort_values(by="start_time").reset_index(drop=True)

            return project, df
