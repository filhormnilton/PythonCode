"""
Centralized configuration for the Business multi-agent system.
All sensitive values are read from environment variables.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.0
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))


@dataclass(frozen=True)
class JiraConfig:
    server: str = field(default_factory=lambda: os.getenv("JIRA_SERVER", "https://your-domain.atlassian.net"))
    user: str = field(default_factory=lambda: os.getenv("JIRA_USER", ""))
    api_token: str = field(default_factory=lambda: os.getenv("JIRA_API_TOKEN", ""))
    project_keys: List[str] = field(
        default_factory=lambda: [
            k.strip()
            for k in os.getenv("JIRA_PROJECT_KEY", "PROJ").split(",")
            if k.strip()
        ]
    )
    team_id: str = field(default_factory=lambda: os.getenv("JIRA_TEAM_ID", ""))

    @property
    def project_key(self) -> str:
        """Return the first (default) project key."""
        return self.project_keys[0] if self.project_keys else ""


@dataclass(frozen=True)
class MiroConfig:
    access_token: str = field(default_factory=lambda: os.getenv("MIRO_ACCESS_TOKEN", ""))
    board_id: str = field(default_factory=lambda: os.getenv("MIRO_BOARD_ID", ""))


@dataclass(frozen=True)
class CamundaConfig:
    rest_url: str = field(default_factory=lambda: os.getenv("CAMUNDA_REST_URL", "http://localhost:8080/engine-rest"))
    user: str = field(default_factory=lambda: os.getenv("CAMUNDA_USER", "demo"))
    password: str = field(default_factory=lambda: os.getenv("CAMUNDA_PASSWORD", "demo"))


@dataclass(frozen=True)
class WebSearchConfig:
    serpapi_key: str = field(default_factory=lambda: os.getenv("SERPAPI_API_KEY", ""))
    tavily_api_key: str = field(default_factory=lambda: os.getenv("TAVILY_API_KEY", ""))


@dataclass(frozen=True)
class TeamsConfig:
    app_id: str = field(default_factory=lambda: os.getenv("TEAMS_APP_ID", ""))
    app_password: str = field(default_factory=lambda: os.getenv("TEAMS_APP_PASSWORD", ""))
    port: int = int(os.getenv("TEAMS_PORT", "3978"))


@dataclass(frozen=True)
class OutputConfig:
    base_dir: Path = field(default_factory=lambda: Path(os.getenv("BUSINESS_OUTPUT_DIR", "./business_output")))

    @property
    def docs_dir(self) -> Path:
        return self.base_dir / "docs"

    @property
    def slides_dir(self) -> Path:
        return self.base_dir / "slides"

    @property
    def diagrams_dir(self) -> Path:
        override = os.getenv("DRAWIO_OUTPUT_DIR", "").strip()
        return Path(override) if override else self.base_dir / "diagrams"

    @property
    def bpmn_dir(self) -> Path:
        return self.base_dir / "bpmn"

    @property
    def knowledge_base_dir(self) -> Path:
        return self.base_dir / "knowledge_base"


@dataclass(frozen=True)
class BusinessConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    jira: JiraConfig = field(default_factory=JiraConfig)
    miro: MiroConfig = field(default_factory=MiroConfig)
    camunda: CamundaConfig = field(default_factory=CamundaConfig)
    web: WebSearchConfig = field(default_factory=WebSearchConfig)
    teams: TeamsConfig = field(default_factory=TeamsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def load_config() -> BusinessConfig:
    return BusinessConfig()


CONFIG = load_config()
