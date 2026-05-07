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
    project = Project(name="RCPSP/MAX Test")
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
        "best": {
            "best": {
                "problem_type": "RCPSP_MAX",
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

    project = Project(name="B&B Test")
    project_repo.create(project)
    activity_repo.create(Activity(id_for_project=0, name="Task 0", project_id=project.id, activity_config_json={}))

    # Simulo l'oggetto BestSolutionBAndB tramite una classe dummy
    class DummyBB:
        def __init__(self, config, solution):
            self.config = config
            self.solution = solution

    class DummySolution:
        def __init__(self, data): self.data = data
        def model_dump(self): return self.data

    class DummyConfig:
        def __init__(self, data): self.data = data
        def model_dump(self): return self.data

    bb_output = DummyBB(
        config=DummyConfig({"durations": [10], "resources": [5]}),
        solution=DummySolution({
            "type": "heuristic_multi_start",
            "best": {
                "best": {"makespan": 10, "schedule": {"0": 0}}
            }
        })
    )

    experiment = data_service.save_solver_result(project.id, bb_output)
    
    assert experiment.experiment_config_json["is_branch_and_bound"] is True
    assert experiment.schedules[0].config_json["parametri_run"]["durations"] == [10]
