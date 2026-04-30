from pydantic import BaseModel

class BestConfigBAndB(BaseModel):
    durations: list[int]
    resources: list[int]
    release_dates: list[int | None]
    due_dates: list[int | None]