from data.database import init_db, engine
from sqlmodel import Session
from datetime import datetime
from data.models import Project, Activity, Experiment, Schedule, ScheduleActivity, ProblemType, Method
from data.repositories.project_repository import ProjectRepository
from data.repositories.activity_repository import ActivityRepository
from data.repositories.experiment_repository import ExperimentRepository
from data.repositories.schedule_repository import ScheduleRepository
from data.repositories.schedule_activity_repository import ScheduleActivityRepository

def test_db_flow():
    print("Initializing Database...")
    init_db()

    with Session(engine) as session:
        project_repo = ProjectRepository(session)
        activity_repo = ActivityRepository(session)
        experiment_repo = ExperimentRepository(session)
        schedule_repo = ScheduleRepository(session)
        sa_repo = ScheduleActivityRepository(session)

        # 1. Create Project with Global Config
        print("Creating Project...")
        project = Project(
            name="Granular Config Project",
            description="Progetto di prova",
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 12, 31),
            initial_budget=10000.0,
            project_config_json={"resources": {"R1": 10, "R2": 20, "R3": 30}, "horizon": 100}
        )
        project_repo.create(project)

        # 2. Create Activity with Specific "Dirty" Config
        print("Creating Activity with local dirty data...")
        act0 = Activity(
            id_for_project=0,
            name="Activity 0",
            is_dummy=True,
            dummy_spec="SOURCE",
            project_id=project.id,
            description="Attività di testing",
            activity_config_json={"duration": 0, "predecessors": [], "successors": [], "release_date": 0, "deadline": 0, "resource_requirements": {"R1": 0, "R2": 0, "R3": 0}}
        )
        act1 = Activity(
            id_for_project=1,
            name="Activity 1",
            is_dummy=False,
            project_id=project.id,
            description="Attività di testing",
            activity_config_json={"duration": (6, 8), "predecessors": [{"id": 0, "type": "FS", "lag": 0, "max_lag": 0}], "successors": [{"id": 2, "type": "FS", "lag": 0, "max_lag": 2}, {"id": 3, "type": "SS", "lag": 0, "max_lag": 2}], "release_date": 0, "deadline": 10, "resource_requirements": {"R1": 2, "R2": 0, "R3": 8}}
        )
        act2 = Activity(
            id_for_project=2,
            name="Activity 2",
            is_dummy=False,
            project_id=project.id,
            description="Attività di testing",
            activity_config_json={"duration": (5, 7), "predecessors": [{"id": 0, "type": "FS", "lag": 0, "max_lag": 2}], "successors": [{"id": 3, "type": "SS", "lag": 0, "max_lag": 2}], "release_date": 0, "deadline": 10, "resource_requirements": {"R1": (6, 8), "R2": (5, 7), "R3": (2, 3)}}
        )
        act3 = Activity(
            id_for_project=3,
            name="Activity 3",
            is_dummy=False,
            project_id=project.id,
            description="Attività di testing",
            activity_config_json={"duration": 7, "predecessors": [{"id": 1, "type": "FS", "lag": 0, "max_lag": 2}, {"id": 2, "type": "FS", "lag": 5, "max_lag": 8}], "successors": [], "release_date": 7, "deadline": 20, "resource_requirements": {"R1": 3, "R2": 8, "R3": 10}}
        )
        act4 = Activity(
            id_for_project=4,
            name="Activity 4",
            is_dummy=True,
            dummy_spec="END",
            project_id=project.id,
            description="Attività di testing",
            activity_config_json={"duration": 0, "predecessors": [{"id": 3, "type": "FS", "lag": 0, "max_lag": 0}, {"id": 2, "type": "FS", "lag": 0, "max_lag": 0}, {"id": 1, "type": "FS", "lag": 0, "max_lag": 0}], "successors": [], "release_date": 0, "deadline": 100, "resource_requirements": {"R1": 0, "R2": 0, "R3": 0}}
        )
        activity_repo.create(act0)
        activity_repo.create(act1)
        activity_repo.create(act2)
        activity_repo.create(act3)
        activity_repo.create(act4)

        # 3. Create Experiment
        print("Creating Experiment...")
        experiment = Experiment(
            project_id=project.id, 
            problem_type=ProblemType.RCPSP_MAX,
            method=Method.HEURISTIC_MULTI_START,
            search_strategy="direct_solver",
            num_runs=2
        )
        experiment_repo.create(experiment)

        # 4. Create Schedule (Fixed Result)
        print("Creating Schedule...")
        schedule1 = Schedule(
            experiment_id=experiment.id,
            makespan=30,
            score=35.6,
            config_json={
                "futura_config_json_per_la_schedula": "PROVA",
            }
            )

        schedule2 = Schedule(
            experiment_id=experiment.id,
            makespan=40,
            score=45.6,
            config_json={
                "futura_config_json_per_la_schedula": "PROVA",
            }
            )
        schedule_repo.create(schedule1)
        schedule_repo.create(schedule2)

        # 5. Create ScheduleActivity (Fixed values)
        print("Creating ScheduleActivity...")
        sa10 = ScheduleActivity(
            schedule_id=schedule1.id, 
            activity_id=act0.id, 
            start_time=0, 
            end_time=0, 
            duration=0,
            resource_usage={"R1": 0, "R2": 0, "R3": 0},
            release_date=0,
            deadline=0
        )
        sa_repo.create(sa10)
        
        sa11 = ScheduleActivity(
            schedule_id=schedule1.id, 
            activity_id=act1.id, 
            start_time=0, 
            end_time=7,
            duration=7,
            resource_usage={"R1": 2, "R2": 0, "R3": 8},
            release_date=0,
            deadline=10
        )
        sa_repo.create(sa11)

        sa12 = ScheduleActivity(
            schedule_id=schedule1.id, 
            activity_id=act2.id, 
            start_time=0, 
            end_time=6, 
            duration=6,
            resource_usage={"R1": 6, "R2": 7, "R3": 3},
            release_date=0,
            deadline=10
        )
        sa_repo.create(sa12)

        sa13 = ScheduleActivity(
            schedule_id=schedule1.id, 
            activity_id=act3.id, 
            start_time=7, 
            end_time=15, 
            duration=8,
            resource_usage={"R1": 3, "R2": 8, "R3": 10},
            release_date=7,
            deadline=20
        )
        sa_repo.create(sa13)

        sa14 = ScheduleActivity(
            schedule_id=schedule1.id, 
            activity_id=act4.id, 
            start_time=15, 
            end_time=15, 
            duration=0,
            resource_usage={"R1": 0, "R2": 0, "R3": 0},
            release_date=0,
            deadline=20
        )
        sa_repo.create(sa14)

        sa20 = ScheduleActivity(
            schedule_id=schedule2.id, 
            activity_id=act0.id, 
            start_time=0, 
            end_time=0, 
            duration=0,
            resource_usage={"R1": 0, "R2": 0, "R3": 0},
            release_date=0,
            deadline=0
        )
        sa_repo.create(sa20)
        
        sa21 = ScheduleActivity(
            schedule_id=schedule2.id, 
            activity_id=act1.id, 
            start_time=0, 
            end_time=7,
            duration=7,
            resource_usage={"R1": 2, "R2": 0, "R3": 8},
            release_date=0,
            deadline=10
        )
        sa_repo.create(sa21)

        sa22 = ScheduleActivity(
            schedule_id=schedule2.id, 
            activity_id=act2.id, 
            start_time=0, 
            end_time=6, 
            duration=6,
            resource_usage={"R1": 8, "R2": 7, "R3": 3},
            release_date=0,
            deadline=10
        )
        sa_repo.create(sa22)

        sa23 = ScheduleActivity(
            schedule_id=schedule2.id, 
            activity_id=act3.id, 
            start_time=7, 
            end_time=15, 
            duration=8,
            resource_usage={"R1": 3, "R2": 8, "R3": 10},
            release_date=7,
            deadline=20
        )
        sa_repo.create(sa23)

        sa24 = ScheduleActivity(
            schedule_id=schedule2.id, 
            activity_id=act4.id, 
            start_time=15, 
            end_time=15, 
            duration=0,
            resource_usage={"R1": 0, "R2": 0, "R3": 0},
            release_date=0,
            deadline=20
        )
        sa_repo.create(sa24)

        # 6. Verification
        print("\n--- Verification ---")
        session.expire_all()
        db_project = project_repo.get_by_id(project.id)
        print(f"Global Capacity: {db_project.project_config_json['resources']}")
        print(f"Horizon: {db_project.project_config_json['horizon']}")
        
        db_activity = db_project.activities[1]
        print(f"Activity Dirty Duration: {db_activity.activity_config_json['duration']}")
        
        db_sa = db_activity.schedule_activities[1]
        print(f"Final Assigned Duration: {db_sa.duration}")

if __name__ == "__main__":
    try:
        test_db_flow()
        print("\nDatabase verification SUCCESSFUL!")
    except Exception as e:
        print(f"\nDatabase verification FAILED: {e}")
        import traceback
        traceback.print_exc()
