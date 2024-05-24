from pydantic import BaseModel, ConfigDict, Field


class Config(BaseModel):
    apscheduler_autostart: bool = True
    apscheduler_log_level: int = 30
    apscheduler_config: dict = Field(
        default_factory=lambda: {"apscheduler.timezone": "Asia/Shanghai"}
    )

    model_config = ConfigDict(extra="ignore")
