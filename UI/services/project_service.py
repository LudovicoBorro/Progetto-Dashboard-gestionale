from solver.dataclasses.input_data import InputData
from data.database import get_session
from data.repositories.project_repository import ProjectRepository
import uuid
from data.models.project import Project, ProjectStatus
from data.models.project_resource import ProjectResource
from datetime import datetime

class ProjectService:
    def __init__(self):
        pass

    @staticmethod
    def get_all_projects():

        with get_session() as session:
            repo = ProjectRepository(session)
            projects = repo.get_all()

        return projects

    @staticmethod
    def get_project_by_id(project_id: uuid.UUID):

        with get_session() as session:
            repo = ProjectRepository(session)
            project = repo.get_by_id(project_id)

        return project

    @staticmethod
    def get_activities_by_project(project_id: uuid.UUID) -> list:
        from data.repositories.activity_repository import ActivityRepository

        with get_session() as session:
            repo = ActivityRepository(session)
            activities = repo.get_by_project(project_id)

        return activities

    @staticmethod
    def get_input_data(project_id: uuid.UUID):

        with get_session() as session:
            repo = ProjectRepository(session)
            project = repo.get_by_id(project_id)
            input_data = InputData.model_validate(project.input_data_json)
            
        return input_data

    @staticmethod
    def create_project(name: str, description: str, start_date: datetime, end_date: datetime,
                       initial_budget: float, resources: list[dict]):

        horizon_days = (end_date - start_date).days
        if horizon_days < 0:
            horizon_days = 0

        with get_session() as session:
            project = Project(
                name=name,
                description=description if description else None,
                start_date=start_date,
                end_date=end_date,
                status=ProjectStatus.NOTSCHEDULED,
                initial_budget=initial_budget,
                final_budget=initial_budget,
                horizon_days=horizon_days,
                num_activities=0
            )
            session.add(project)
            session.flush()

            for res in resources:
                resource = ProjectResource(
                    project_id=project.id,
                    name=res["name"],
                    capacity_min=res["capacity_min"],
                    capacity_max=res.get("capacity_max"),
                    color_hex=res.get("color_hex", "#FFFFFF")
                )
                session.add(resource)

            session.commit()
            session.refresh(project)
            
            # Trigger lazy load of resources so they are available out of session
            _ = project.resources
            
            return project

    @staticmethod
    def update_project_info(project: Project):
        with get_session() as session:
            repo = ProjectRepository(session)
            repo.update(project)

    @staticmethod
    def update_project_status(project_id: uuid.UUID, status: ProjectStatus):
        with get_session() as session:
            repo = ProjectRepository(session)
            repo.update_status(project_id, status)

    @staticmethod
    def delete_project(project_id: uuid.UUID):
        with get_session() as session:
            repo = ProjectRepository(session)
            repo.delete(project_id)
