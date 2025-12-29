from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yardmaster.core.release import ReleaseSpec


@dataclass(frozen=True, slots=True)
class ValidationResult:
    ok: bool
    warnings: list[str]
    errors: list[str]


class ReleaseValidator:
    def validate_unique_channels(self, specs: Sequence[ReleaseSpec]) -> ValidationResult:
        seen: set = set()
        errors = []
        for spec in specs:
            if spec.channel in seen:
                errors.append(f"Duplicate channel specified: {spec.channel.value}")
            seen.add(spec.channel)
        return ValidationResult(ok=not errors, warnings=[], errors=errors)

    def validate_version_progression(self, specs: Sequence[ReleaseSpec]) -> ValidationResult:
        warnings = [
            f"Version '{spec.version}' for {spec.channel.value} looks unusually low."
            for spec in specs
            if spec.version.epoch < 1000
        ]
        return ValidationResult(ok=True, warnings=warnings, errors=[])
