from pydantic import BaseModel, Field
from typing import List, Optional

class TaskRequest(BaseModel):
    task: str = Field(..., description="Description of the task to break down")
    validate_searches: bool = Field(default=False, description="Whether to validate searches with Google")

class SearchResult(BaseModel):
    title: str
    link: str
    snippet: str

class SearchValidation(BaseModel):
    is_verified: bool
    search_results: List[SearchResult]
    recommended_result: Optional[int] = None

class Step(BaseModel):
    step_number: int
    description: str
    search_query: str
    expected_results: str
    key_phrases: List[str]
    alternative_searches: List[str]
    instructions: str
    validation: Optional[SearchValidation] = None

class WorkflowResponse(BaseModel):
    task: str
    task_summary: str
    steps: List[Step]
    total_steps: int
    estimated_time: str
    difficulty: str

