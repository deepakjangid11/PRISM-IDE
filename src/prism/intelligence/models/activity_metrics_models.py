from pydantic import BaseModel, ConfigDict


class ActivityMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    developer_id: str
    project_path: str

    total_events: int
    code_edits: int
    file_opens: int
    file_saves: int
    test_runs: int
    test_failures: int
    test_successes: int
    errors: int
    ai_help_requests: int
    files_touched: int
