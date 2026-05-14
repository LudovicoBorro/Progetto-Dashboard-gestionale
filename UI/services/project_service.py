from solver.dataclasses.input_data import InputData
from data.database import get_session
from data.repositories.project_repository import ProjectRepository
import uuid

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
        