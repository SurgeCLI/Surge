from dataclasses import dataclass


@dataclass(frozen=True)
class SystemSnapshot:
    timestamp: int
    cpu_util: float
    mem_util: float
    disk_util: float
    load_1m: float
    load_5m: float
    load_15m: float
    ...
    raw_uptime: str = None
    raw_free: str = None
    raw_df: str = None

    def to_dict(self):
        return {
            
        }
