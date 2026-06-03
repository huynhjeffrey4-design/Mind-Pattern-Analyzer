from pydantic import BaseModel


class UserSettingsUpdate(BaseModel):
    ai_analysis_enabled: bool | None = None
    weekly_summary_enabled: bool | None = None


class UserSettingsResponse(BaseModel):
    id: int
    email: str
    display_name: str | None
    ai_analysis_enabled: bool
    weekly_summary_enabled: bool

    model_config = {"from_attributes": True}
