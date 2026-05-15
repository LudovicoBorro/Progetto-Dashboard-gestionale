import pytest
import uuid
from sqlmodel import Session, SQLModel, create_engine
from data.models import Project, Activity, ProblemType, Method
from data.repositories.project_repository import ProjectRepository
from data.repositories.activity_repository import ActivityRepository
from data.services.data_service import DataService

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
    project = Project(name="RCPSP/MAX Test", end_date=datetime.now() + timedelta(days=30))
    project_repo.create(project)
    
    # Attività con resource requirements nel JSON
    activity_repo.create(Activity(
        id_for_project=0, name="Task 0", project_id=project.id,
        activity_config_json={"resource_requirements": {"R1": 5}}
    ))

    # 2. Simulated RCPSP/MAX Output
    simulated_output = {
        "type": "exact",
        "problem_difficulty": "easy",
        "problem_type": "RCPSP_MAX",
        "best": {
            "best": {
                "makespan": 15,
                "penalità": 2.0,
                "score": 19.0,
                "soluzione": [{"activity": 0, "start": 5, "end": 10}],
                "config": {
                    "release_dates": [2],
                    "due_dates": [20]
                }
            }
        }
    }

    # 3. Call
    experiment = data_service.save_solver_result(project.id, simulated_output)

    # 4. Assertions
    assert experiment.problem_type == ProblemType.RCPSP_MAX
    schedule = experiment.schedules[0]
    assert schedule.score == 19.0
    assert schedule.config_json["penalità_totale"] == 2.0
    
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
    project = Project(name="B&B Test", end_date=datetime.now() + timedelta(days=30))
    project_repo.create(project)
    activity_repo.create(Activity(id_for_project=0, name="Task 0", project_id=project.id, activity_config_json={}))

    # Simulo un output compatibile con SolutionDTO tramite dict (legacy support)
    bb_output = {
        "type": "heuristic_multi_start",
        "solution_type": "heuristic_multi_start",
        "problem_difficulty": "medium",
        "search_strategy": "branch_and_bound",
        "additional_info": {
            "best_config": {"durations": [10], "resources": [5]},
            "nodes_explored": 42
        },
        "best": {
            "best": {"makespan": 10, "soluzione": [{"activity": 0, "start": 0, "end": 10}]}
        }
    }

    experiment = data_service.save_solver_result(project.id, bb_output)
    
    assert experiment.method == Method.HEURISTIC_MULTI_START
    assert experiment.search_strategy == "branch_and_bound"
    assert experiment.experiment_config_json["additional_info"]["nodes_explored"] == 42
    assert experiment.schedules[0].config_json["parametri_run"]["durations"] == [10]
