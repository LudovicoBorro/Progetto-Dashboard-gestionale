from pandas._testing import loc
from data.models.project import Project
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import datetime as dt
from utils.converter.calendar_utils import generate_working_dates
from utils.scheduling.progress_utils import calculate_expected_progress

class GanttChart:
    """
    Questa classe crea un grafico di Gantt partendo da un dataframe 
    contenente le seguenti colonne:
    - activity
    - resource
    - start_time (working_days)
    - end_time (working_days)
    - start_date (working_days)
    - end_date (working_days)
    - activity_duration (working_days)
    - completion_frac (0-1)
    - completion_days (progress * activity_duration)
    """

    def __init__(self, dataframe: pd.DataFrame, project: Project):
        self.df = dataframe
        self.project = project

    def _compute_tracking(self, today_idx):
        expected_progresses = []
        variances = []
        delays = []

        for _, row in self.df.iterrows():
            expected_progress = calculate_expected_progress(
                start_time=row["start_time"],
                duration=row["activity_duration"],
                today_idx=today_idx
            )

            variance = row["completion_frac"] - expected_progress

            expected_progresses.append(expected_progress)
            variances.append(variance)
            delays.append(variance < -0.05)

        self.df["expected_progress"] = expected_progresses
        self.df["variance"] = variances
        self.df["delay"] = delays

    def _build_colors(self):
        activity_colors = {}
        for activity in self.df["activity"].unique():
            # Determina un colore persistente in base all'hashing dell'attività
            # Usiamo tab20 che ha 20 colori distinti
            rgba = plt.colormaps.get_cmap('tab20')(hash(activity) % 20)
            activity_colors[activity] = matplotlib.colors.to_hex(rgba)
        return activity_colors

    def _compute_calendar(self, max_day, today):
        # genera solo date lavorative
        working_dates = generate_working_dates(
            start_date=self.project.start_date,
            num_days=max_day + 1,
            from_today=False
        )

        if today in working_dates:  
            today_idx = working_dates.index(today)
        elif today < working_dates[0]:
            today_idx = 0
        else:
            today_idx = max_day

        return working_dates, today_idx, self._build_colors()

    def plot(self):
        fig, ax = plt.subplots(figsize=(14, 6))

        # massimo working day
        max_day = int(self.df["end_time"].max())

        today = dt.date.today()
        
        working_dates, today_idx, activity_colors = self._compute_calendar(max_day, today)
        self._compute_tracking(today_idx)

        progress_patches = [matplotlib.patches.Patch(label="Durata pianificata (barra chiara)", color="gray", alpha=0.4, linewidth=None),
                            matplotlib.patches.Patch(label="Progresso effettivo (barra scura)", color="gray", alpha=1.0)]

        for index, row in self.df.iterrows():

            is_delayed = row["delay"]
            
            # Barra chiara per l'intera durata dell'attività
            ax.barh(
                y=row["activity"],
                width=row["activity_duration"],
                left=row["start_time"],
                color=activity_colors[row["activity"]],
                alpha=0.4,
                edgecolor="red" if is_delayed else None,
                linewidth=3 if is_delayed else 0,
            )

            # Barra colorata per l'avanzamento reale dell'attività
            ax.barh(
                y=row["activity"],
                width=row["completion_days"],
                left=row["start_time"],
                color=activity_colors[row["activity"]],
                alpha=1.0
            )

        ax.set_title(self.project.name, fontsize=20)
        ax.invert_yaxis()

        # tick ogni 5 working days
        xticks = np.arange(0, max_day + 1, 5)
        xticklabels = [
            working_dates[i].strftime('%d/%m')
            for i in xticks
        ]
        ax.set_xticks(xticks)
        ax.set_xticklabels(xticklabels)
        ax.xaxis.grid(True, alpha=0.5)
        ax.legend(handles=progress_patches, fontsize=11, title='Legenda', loc="upper right")

        ax.axvline(x=today_idx, color='r', linestyle='dashed', linewidth=2)
        ax.text(x=today_idx+0.3, y=len(self.df["activity"].unique())-0.5, s=today.strftime('%d/%m'), color='r', fontsize=10)

        plt.tight_layout()
        
        return fig, ax

if __name__ == "__main__":
    
    df = pd.DataFrame(
        {
            "activity": [
                "Requirements Analysis",
                "Database Design",
                "Backend Development",
                "Frontend Development",
                "API Integration",
                "Testing",
                "Bug Fixing",
                "Deployment",
                "Documentation",
                "Final Review"
            ],

            "resource": [
                "Business Analyst",
                "DB Engineer",
                "Backend Team",
                "Frontend Team",
                "Integration Team",
                "QA Team",
                "Backend Team",
                "DevOps",
                "Technical Writer",
                "Project Manager"
            ],

            # Working days timeline
            "start_time": [
                0,
                2,
                5,
                5,
                11,
                15,
                18,
                21,
                16,
                23
            ],

            "end_time": [
                2,
                5,
                11,
                12,
                15,
                18,
                21,
                22,
                20,
                24
            ],

            "activity_duration": [
                2,
                3,
                6,
                7,
                4,
                3,
                3,
                1,
                4,
                1
            ],

            # Date reali
            "start_date": pd.to_datetime([
                "2026-04-28",
                "2026-04-30",
                "2026-05-05",
                "2026-05-05",
                "2026-05-13",
                "2026-05-19",
                "2026-05-22",
                "2026-05-27",
                "2026-05-20",
                "2026-05-29"
            ]),

            "end_date": pd.to_datetime([
                "2026-04-30",
                "2026-05-05",
                "2026-05-13",
                "2026-05-14",
                "2026-05-19",
                "2026-05-22",
                "2026-05-27",
                "2026-05-28",
                "2026-05-26",
                "2026-05-30"
            ]),

            # Stato reale del progetto
            "completion_frac": [

                # COMPLETATA
                1.0,

                # COMPLETATA
                1.0,

                # IN RITARDO
                # dovrebbe essere ~100%
                0.55,

                # LEGGERMENTE IN RITARDO
                # dovrebbe essere ~90%
                0.65,

                # MOLTO IN RITARDO
                # dovrebbe essere ~75%
                0.25,

                # APPENA INIZIATA
                0.10,

                # NON ANCORA INIZIATA
                0.0,

                # FUTURA
                0.0,

                # IN ANTICIPO
                # dovrebbe essere ~25%
                0.75,

                # FUTURA
                0.0
            ],

            "completion_days": [
                2,
                3,
                3.3,
                4.55,
                1,
                0.3,
                0,
                0,
                3,
                0
            ]
        }
    )
    project = Project(id="00001", name="Progetto di prova per Gantt", end_date=pd.to_datetime('2026-05-30'), start_date=pd.to_datetime('2026-04-28') )
    gantt = GanttChart(df, project)
    gantt.plot()