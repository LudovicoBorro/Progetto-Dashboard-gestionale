from pydantic import BaseModel

class BaseDataBAndB(BaseModel):
    n: int
    durations: list[int | tuple[int, int]]
    precedences: list[tuple[int, int, str, int, int | None]]
    resources: list[int | tuple[int, int]]
    horizon: int
    release_dates: list[int | None | tuple[int, int]]
    due_dates: list[int | None | tuple[int, int]]
    consumption: list[list[int]]