"""Temperature logger and watchdog for a GPU machine (system python3, no dependencies).

Every INTERVAL seconds one CSV line: GPU temperature, power, SM clock, pstate, active clock-event reasons,
HW/SW thermal slowdown counters, maximum over /sys/class/thermal/thermal_zone*/temp, NVMe temperature.

The watchdog acts on the hottest thermal zone (not the GPU sensor) and only on your own processes: processes of
this user whose executable lies under --match (default: the work directory, e.g. its venv python). The watchdog
itself must run with a python outside that directory (e.g. /usr/bin/python3), so it never stops itself.
  zone >= PAUSE  -> SIGSTOP all own jobs; SIGCONT once zone < RESUME
  zone >= KILL or any rise of the HW/SW thermal-slowdown counters
                 -> terminate all own jobs, write <work dir>/STOP (run.sh starts no further job)

Work directory: --base, else $THERMO_BASE, else ~/thermo-work.

  /usr/bin/python3 thermo.py [--base DIR] [--pause 85] [--resume 70] [--kill 90] [--interval 5] [--match PREFIX]
"""
import argparse
import glob
import os
import signal
import subprocess
import time
from pathlib import Path

FIELDS = ("temperature.gpu,power.draw,clocks.sm,pstate,clocks_event_reasons.active,"
          "clocks_event_reasons_counters.hw_thermal_slowdown,clocks_event_reasons_counters.sw_thermal_slowdown")
HEADER = "timestamp,gpu_temp_c,power_w,sm_mhz,pstate,event_reasons,hw_thermal_us,sw_thermal_us,zone_max_c,nvme_c,state"


def zone_max():
    vals = []
    for p in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
        try:
            vals.append(int(open(p).read()) / 1000)
        except (OSError, ValueError):
            pass
    return max(vals) if vals else float("nan")


def nvme():
    for d in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            if open(f"{d}/name").read().strip() == "nvme":
                return int(open(f"{d}/temp1_input").read()) / 1000
        except (OSError, ValueError):
            pass
    return float("nan")


def gpu():
    try:
        out = subprocess.run(["nvidia-smi", f"--query-gpu={FIELDS}", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=20).stdout.strip().splitlines()[0]
        return [s.strip() for s in out.split(",")]
    except Exception:
        return ["nan"] * 7


def own_jobs(prefix):
    me, pids = os.getuid(), []
    for d in glob.glob("/proc/[0-9]*"):
        try:
            if os.stat(d).st_uid != me:
                continue
            exe = os.path.realpath(f"{d}/exe")
            if exe.startswith(prefix) and int(d[6:]) != os.getpid():
                pids.append(int(d[6:]))
        except OSError:
            pass
    return pids


def signal_all(pids, sig):
    for p in pids:
        try:
            os.kill(p, sig)
        except OSError:
            pass


def num(s):
    try:
        return float(s)
    except ValueError:
        return float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.environ.get("THERMO_BASE", str(Path.home() / "thermo-work")))
    ap.add_argument("--pause", type=float, default=85)
    ap.add_argument("--resume", type=float, default=70)
    ap.add_argument("--kill", type=float, default=90)
    ap.add_argument("--interval", type=float, default=5)
    ap.add_argument("--match", help="executable path prefix of the jobs to control (default: <base>/)")
    args = ap.parse_args()
    base = Path(args.base).expanduser().resolve()
    logs = base / "logs"
    match = args.match or str(base) + "/"
    stop = base / "STOP"
    logs.mkdir(parents=True, exist_ok=True)
    csv = logs / "temp.csv"
    if not csv.exists():
        csv.write_text(HEADER + "\n")
    wlog = open(logs / "watchdog.log", "a", buffering=1)

    def say(msg):
        wlog.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")

    say(f"watchdog started: pause {args.pause}, resume {args.resume}, kill {args.kill}, match {match}")
    counters, paused, killed = None, False, stop.exists()
    while True:
        g = gpu()
        z, n = zone_max(), nvme()
        now = (num(g[5]), num(g[6]))
        if counters is None and all(v == v for v in now):
            counters = now
            say(f"slowdown counters at start: hw {now[0]:.0f} us, sw {now[1]:.0f} us")
        rose = counters is not None and any(v == v and v > c for v, c in zip(now, counters))
        if rose or z >= args.kill:
            jobs = own_jobs(match)
            if jobs or not killed:
                say(f"KILL: zone {z:.1f} C, counters {counters} -> {now}; terminating own jobs {jobs}")
                stop.write_text(time.strftime("%F %T") + f" zone {z:.1f} counters {counters} -> {now}\n")
                signal_all(jobs, signal.SIGTERM)
                signal_all(jobs, signal.SIGCONT)  # stopped processes only handle SIGTERM once continued
                time.sleep(5)
                signal_all(own_jobs(match), signal.SIGKILL)
                killed, paused = True, False
            if rose:
                counters = now
        elif z >= args.pause and not paused:
            jobs = own_jobs(match)
            signal_all(jobs, signal.SIGSTOP)
            paused = True
            say(f"PAUSE: zone {z:.1f} C >= {args.pause}; SIGSTOP {jobs}")
        elif paused and z < args.resume:
            jobs = own_jobs(match)
            signal_all(jobs, signal.SIGCONT)
            paused = False
            say(f"RESUME: zone {z:.1f} C < {args.resume}; SIGCONT {jobs}")
        elif paused:
            signal_all(own_jobs(match), signal.SIGSTOP)  # jobs started while paused
        state = "killed" if killed else ("paused" if paused else "run")
        with open(csv, "a") as f:
            f.write(",".join([time.strftime("%Y/%m/%d %H:%M:%S"), *g[:5], g[5], g[6], f"{z:.1f}", f"{n:.2f}", state])
                    + "\n")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
