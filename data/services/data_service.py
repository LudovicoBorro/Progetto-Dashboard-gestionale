import uuid
from typing import Union, Dict, List, Any
from sqlmodel import Session
from ..models import Experiment, Schedule, ScheduleActivity, Activity, ProblemType, Method, ProjectStatus
from ..repositories.experiment_repository import ExperimentRepository
from ..repositories.schedule_repository import ScheduleRepository
from ..repositories.schedule_activity_repository import ScheduleActivityRepository
from ..repositories.activity_repository import ActivityRepository
from ..repositories.project_repository import ProjectRepository
from solver.dataclasses.soluzione_orchestrator import SolutionDTO

class DataService:
    def __init__(self, session: Session):
        self.session = session
        self.experiment_repo = ExperimentRepository(session)
        self.schedule_repo = ScheduleRepository(session)
        self.sa_repo = ScheduleActivityRepository(session)
        self.activity_repo = ActivityRepository(session)
        self.project_repository = ProjectRepository(session)

    def save_solver_result(self, project_id: uuid.UUID, solver_output: SolutionDTO) -> Experiment:
        """
        Mappa e salva i risultati dell'orchestrator nel database usando il nuovo SolutionDTO.
        """
        # 1. Identificazione tipo di output e configurazione globale
        orchestrator_data = solver_output
        
        is_bb = (orchestrator_data.search_strategy== "branch_and_bound")

        # 2. Creazione Experiment
        # Leggiamo il tipo di problema dal flag esplicito dell'orchestrator
        problem_type_str = orchestrator_data.problem_type
        
        experiment = Experiment(
            project_id=project_id,
            problem_type=ProblemType(problem_type_str),

            method=Method(orchestrator_data.solution_type),
            num_runs=orchestrator_data.n_runs,

            experiment_config_json={
                "difficulty": orchestrator_data.problem_difficulty,
                "is_branch_and_bound": is_bb,
                "global_solver_results": orchestrator_data.results
            }
        )
        self.experiment_repo.create(experiment)

        # 4. Mappatura Activity ID
        activities = self.activity_repo.get_by_project(project_id)
        activity_map: Dict[int, Activity] = {a.id_for_project: a for a in activities}

        # 4. Elaborazione delle Top-K soluzioni
        ranking = orchestrator_data.ranking
        seen_schedules = set()
        all_top_solutions = []
        
        # Consideriamo sia le migliori per makespan che per score
        sources = [ranking.top_k_makespan or [], ranking.top_k_score or []]

        for source in sources:

            for sol in source:

                signature = (
                    tuple(sorted(sol.schedule_dict.items()))
                    if sol.schedule_dict
                    else tuple(
                        (a["activity"], a["start"])
                        for a in sol.soluzione or []
                    )
                )

                if signature not in seen_schedules:
                    seen_schedules.add(signature)
                    all_top_solutions.append(sol)

        # 5. Schedule
        for sol in all_top_solutions:

            new_schedule = Schedule(
                experiment_id=experiment.id,

                makespan=sol.makespan,
                score=sol.score,

                config_json={
                    "regola_usata": sol.regola,
                    "penalty": sol.penalty,
                    "elapsed_time": sol.elapsed_time,
                    "rank_info": sol.rank_info
                }
            )

            self.schedule_repo.create(new_schedule)

            # Caso 1. Schedule presente in sol.soluzione
            if sol.soluzione:

                for item in sol.soluzione:

                    act_id = item["activity"]

                    if act_id not in activity_map:
                        continue

                    activity = activity_map[act_id]

                    consumption = activity.activity_config_json.get("consumption", {})
                    resource_usage = {}
                    for i, cons in enumerate(consumption):
                        resource_usage["R"+str((i+1))] = cons

                    release_date = activity.activity_config_json.get("release_date")
                    due_date = activity.activity_config_json.get("due_date")

                    sa = ScheduleActivity(
                        schedule_id=new_schedule.id,
                        activity_id=activity.id,

                        start_time=item["start"],
                        end_time=item["end"],
                        duration=item["end"] - item["start"],

                        resource_usage=resource_usage,
                        release_date=release_date,
                        deadline=due_date
                    )

                    self.sa_repo.create(sa)

            # Caso 2. Schedule presente in sol.schedule_dict
            elif sol.schedule_dict:

                durations = sol.durations or {}

                for act_id_raw, start in sol.schedule_dict.items():

                    act_id = int(act_id_raw)

                    if act_id not in activity_map:
                        continue

                    activity = activity_map[act_id]

                    if isinstance(durations, list):
                        duration = durations[act_id]
                    else:
                        duration = durations.get(str(act_id), 0)

                    sa = ScheduleActivity(
                        schedule_id=new_schedule.id,
                        activity_id=activity.id,

                        start_time=start,
                        end_time=start + duration,
                        duration=duration,

                        resource_usage=activity.activity_config_json.get(
                            "resource_requirements", {}
                        )
                    )

                    self.sa_repo.create(sa)

        self.project_repository.update_status(project_id, ProjectStatus.SCHEDULED)

        print("[DEBUG]: Salvato correttamente i dati nel DB.")
        return experiment
