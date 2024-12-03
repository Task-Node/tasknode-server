from typing import TypedDict, List, Optional


class BoundingBox(TypedDict):
    width: float
    height: float
    left: float
    top: float


class DocField(TypedDict):
    page: int
    key: str
    value: Optional[str]
    boundingBox: BoundingBox
    isSelection: bool


class ProcessDocResponse(TypedDict):
    file_url: str
    fields: List[DocField]
