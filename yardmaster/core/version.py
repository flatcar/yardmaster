from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Channel(str, Enum):
    alpha = "alpha"
    beta = "beta"
    stable = "stable"
    lts = "lts"


STREAM_TO_CHANNEL: dict[int, Channel] = {
    0: Channel.alpha,
    1: Channel.beta,
    2: Channel.stable,
    3: Channel.lts,
}
CHANNEL_TO_STREAM: dict[Channel, int] = {ch: stream for stream, ch in STREAM_TO_CHANNEL.items()}


@dataclass(frozen=True, slots=True)
class Version:
    epoch: int
    stream: int
    revision: int = 0

    @classmethod
    def parse(cls, s: str) -> Version:
        parts = s.strip().split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version '{s}'. Expected 3 dot-separated integers.")
        epoch, stream, revision = (int(p) for p in parts)
        return cls(epoch, stream, revision)

    def is_major_release(self) -> bool:
        return self.revision == 0

    def to_tuple(self) -> tuple[int, int, int]:
        return (self.epoch, self.stream, self.revision)

    def __str__(self) -> str:
        return f"{self.epoch}.{self.stream}.{self.revision}"
