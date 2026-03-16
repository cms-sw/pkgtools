import subprocess
from threading import Thread
import psutil
from json import dump as json_dump
from time import time, sleep, monotonic

# Sampling interval in seconds
SAMPLE_INTERVAL = 1.0
cpu_times = {}

def update_monitor_stats(proc, commands=False):
    global cpu_times
    try:children = proc.children(recursive=True)
    except: return {}
    stats = {"rss": 0, "vms": 0, "shared": 0, "data": 0, "uss": 0, "pss": 0, "num_fds": 0, "num_threads": 0, "processes": 0, "cpu": 0}
    if commands:
        stats["commands" ] = []
    stats['processes'] = len(children)
    sleep(SAMPLE_INTERVAL)
    new_cpu_times = {}
    for p in [proc] + children:
        pid = p.pid
        try:
            current_time = monotonic()
            new_cpu = p.cpu_times()
            old_cpu, last_time = cpu_times.get(pid, (None, None))
            cpu_delta = 0
            elapsed = 0
            if old_cpu:
                delta = (new_cpu.user - old_cpu.user) + (new_cpu.system - old_cpu.system)
                elapsed = current_time - last_time
            else:
                delta = new_cpu.user + new_cpu.system
                elapsed = time() - p.create_time()
            pcpu = 0
            if elapsed>=0.1:
                pcpu = int((delta / elapsed) * 100.0)
                stats["cpu"] += pcpu
            if commands:
                stats["commands"].append({"pid": pid, "command": " ".join(p.cmdline())[:200], "old_cpu": old_cpu, "new_cpu": new_cpu, "delta": delta, "elapsed": elapsed, "cpu": pcpu, "threads": p.num_threads()})
            new_cpu_times[pid] = (new_cpu, current_time)
        except:
            continue
        try:
            stats['num_fds'] += p.num_fds()
            stats['num_threads'] += p.num_threads()
            mem = None
            try:
                mem = p.memory_full_info()
                for a in ["uss", "pss"]: stats[a] += getattr(mem, a)
            except:
                try:    mem = p.memory_info()
                except: mem = p.memory_info_ex()
            for a in ["rss", "vms", "shared", "data"]: stats[a] += getattr(mem, a)
        except: pass
    cpu_times = new_cpu_times
    return stats

def monitor_stats(p_id, stats_file_name, commands=False):
    stime = int(time())
    p = psutil.Process(p_id)
    data = []
    while p.is_running():
        stats = update_monitor_stats(p, commands)
        if not stats:
            sleep(SAMPLE_INTERVAL)
            continue
        stats['time'] = int(time()-stime)
        data.append(stats)
    with open(stats_file_name, "w") as sf:
        json_dump(data, sf)
    return

def run_monitor_on_command(command_to_monitor, stats_file_name, commands=False):
    p = subprocess.Popen(command_to_monitor, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds= True)
    mon_thd = Thread(target=monitor_stats, args=(p.pid, stats_file_name, commands,))
    mon_thd.start()
    stout, sterr = p.communicate() # this blocks until the process is finished
    mon_thd.join() # wait for monitoring thread to write its output
    return p.returncode, stout
