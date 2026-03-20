"""Abstract base class for tool parsers."""
from abc import ABC, abstractmethod
from pathlib import Path
from ai_rules.models import RuleGroup

class BaseParser(ABC):
    @abstractmethod
    def parse(self, path: Path) -> list[RuleGroup]: ...
    @abstractmethod
    def convert(self, rules: list[RuleGroup]) -> dict[str, str]: ...
    @abstractmethod
    def write(self, rules: list[RuleGroup], target_path: Path) -> None: ...
