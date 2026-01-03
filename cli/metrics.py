from app import get_load, get_cpu, get_memory, get_disk
from models import MetricSnapshot
from time import time


def collect_system_snapshot() -> MetricSnapshot:
    load, _ = get_load()
    _, _, idle = get_cpu()
    total, used, _ = get_memory()
    _, _, _, disk_percent = get_disk()

    cpu_util = 100.0 - idle
    mem_util = (used / total * 100) if total else 0.0

    return MetricSnapshot(
        timestamp=int(time()),
        cpu_util=cpu_util,
        mem_util=mem_util,
        disk_util=disk_percent,
        load_1m=load[0],
        load_5m=load[1],
        load_15m=load[2],
    )


def calculate_mem_velocity(current: MetricSnapshot, prev: MetricSnapshot) -> float:
    d_mem = current.mem_util - prev.mem_util
    d_t = current.timestamp - prev.timestamp

    if d_t == 0:
        return 0.0
    return d_mem / d_t * 60
