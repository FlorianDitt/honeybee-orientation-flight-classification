"""In-process load governor (in addition to the external watchdog thermo.py).

Call tick() often in your training loop (e.g. per batch or per epoch). It
  1. keeps a duty cycle: after `work` seconds of computing it sleeps work * (1 / DUTY - 1);
  2. reads the hottest thermal zone; at >= SOFT_HIGH it sleeps until the zone is <= SOFT_LOW.
Environment: GOV_DUTY (default 0.5), GOV_SOFT_HIGH (75), GOV_SOFT_LOW (70), GOV_CHUNK (0.25 s of work per cycle).

    try:
        import gov
    except ImportError:   # e.g. on the laptop
        gov = None
    for epoch in ...:
        ...
        if gov:
            gov.tick()
"""
import glob
import os
import sys
import time

DUTY = float(os.environ.get("GOV_DUTY", "0.5"))
SOFT_HIGH = float(os.environ.get("GOV_SOFT_HIGH", "75"))
SOFT_LOW = float(os.environ.get("GOV_SOFT_LOW", "70"))
CHUNK = float(os.environ.get("GOV_CHUNK", "0.25"))
_last = time.time()
stats = {"duty_sleep": 0.0, "hot_sleep": 0.0, "hot_events": 0}


def zone_max():
    vals = []
    for p in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
        try:
            vals.append(int(open(p).read()) / 1000)
        except (OSError, ValueError):
            pass
    return max(vals) if vals else 0.0


def _sync():
    torch = sys.modules.get("torch")  # only if the caller uses torch: wait for queued GPU work, else time is wrong
    if torch is not None and torch.cuda.is_available():
        torch.cuda.synchronize()


def tick():
    global _last
    _sync()
    now = time.time()
    work = now - _last
    if work < CHUNK:  # collect at least CHUNK seconds of work, so the pause is long enough for the GPU to idle
        return
    z = zone_max()  # read before the pause: the zone drops within seconds once the load stops
    if DUTY < 1:
        pause = min(work * (1 / DUTY - 1), 120)
        time.sleep(pause)
        stats["duty_sleep"] += pause
    if z >= SOFT_HIGH:
        stats["hot_events"] += 1
        t0 = time.time()
        print(time.strftime("%H:%M:%S"), f"gov: zone {z:.1f} C >= {SOFT_HIGH}, waiting for <= {SOFT_LOW}",
              file=sys.stderr, flush=True)
        while zone_max() > SOFT_LOW:
            time.sleep(5)
        stats["hot_sleep"] += time.time() - t0
    _last = time.time()


def summary():
    return (f"gov: duty {DUTY}, duty sleep {stats['duty_sleep']:.0f} s, hot events {stats['hot_events']}, "
            f"hot sleep {stats['hot_sleep']:.0f} s")
