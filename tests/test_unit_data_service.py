import pytest
import uuid
from sqlmodel import Session, SQLModel, create_engine
from data.models import Project, Activity, ProblemType, Method, ProjectStatus
from data.repositories.project_repository import ProjectRepository
from data.repositories.activity_repository import ActivityRepository
from data.services.data_service import DataService
from solver.dataclasses.soluzione_orchestrator import SolutionDTO

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()

def test_save_rcpsp_max_result(session: Session):
    project_repo = ProjectRepository(session)
    activity_repo = ActivityRepository(session)
    data_service = DataService(session)

    # 1. Setup
    from datetime import datetime, timedelta
    project = Project(
        name="RCPSP/MAX Test",
        end_date=datetime.now() + timedelta(days=30),
        status=ProjectStatus.NOTSCHEDULED
    )
    project_repo.create(project)
    
    # Attività con dati nel formato atteso da DataService.
    activity_repo.create(Activity(
        id_for_project=0, name="Task 0", project_id=project.id,
        activity_config_json={
            "consumption": [5],
            "release_date": 2,
            "due_date": 20
        }
    ))

    # 2. Output nel formato corrente dell'orchestrator.
    simulated_output = SolutionDTO.model_validate({
        "type": "exact",
        "problem_difficulty": "easy",
        "problem_type": "RCPSP_MAX",
        "n_runs": 1,
        "ranking": {
            "best_solution": {
                "makespan": 15,
                "penalty": 2.0,
                "score": 19.0,
                "soluzione": [{"activity": 0, "start": 5, "end": 10}]
            },
            "top_k_makespan": [{
                "makespan": 15,
                "penalty": 2.0,
                "score": 19.0,
                "soluzione": [{"activity": 0, "start": 5, "end": 10}]
            }],
            "top_k_score": []
        }
    })

    # 3. Call
    experiment = data_service.save_solver_result(project.id, simulated_output)

    # 4. Assertions
    assert experiment.problem_type == ProblemType.RCPSP_MAX
    schedule = experiment.schedules[0]
    assert schedule.score == 19.0
    assert schedule.config_json["penalty"] == 2.0
    
    sa = schedule.schedule_activities[0]
    assert sa.start_time == 5
    assert sa.release_date == 2
    assert sa.deadline == 20
    assert sa.resource_usage == {"R1": 5}

def test_save_bb_result(session: Session):
    project_repo = ProjectRepository(session)
    activity_repo = ActivityRepository(session)
    data_service = DataService(session)

    from datetime import datetime, timedelta
    project = Project(
        name="B&B Test",
        end_date=datetime.now() + timedelta(days=30),
        status=ProjectStatus.NOTSCHEDULED
    )
    project_repo.create(project)
    activity_repo.create(Activity(id_for_project=0, name="Task 0", project_id=project.id, activity_config_json={}))

    # Output B&B nel formato corrente dell'orchestrator.
    bb_output = SolutionDTO.model_validate({
        "type": "heuristic_multi_start",
        "problem_difficulty": "medium",
        "problem_type": "RCPSP",
        "n_runs": 1,
        "search_strategy": "branch_and_bound",
        "additional_info": {
            "best_config": {"durations": [10], "resources": [5]},
            "nodes_explored": 42
        },
        "ranking": {
            "best_solution": {"makespan": 10, "soluzione": [{"activity": 0, "start": 0, "end": 10}]},
            "top_k_makespan": [{"makespan": 10, "soluzione": [{"activity": 0, "start": 0, "end": 10}]}],
            "top_k_score": []
        }
    })

    experiment = data_service.save_solver_result(project.id, bb_output)
    
    assert experiment.method == Method.HEURISTIC_MULTI_START
    assert experiment.experiment_config_json["is_branch_and_bound"] is True
    assert experiment.experiment_config_json["difficulty"] == "medium"
    assert experiment.schedules[0].makespan == 10
