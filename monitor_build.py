import subprocess
from threading import Thread
import psutil
from json import dump as json_dump
from time import time, sleep

# Sampling interval in seconds
SAMPLE_INTERVAL = 1.0
cpu_initialized = set()

def update_monitor_stats(proc):
    global cpu_initialized
    children = []
    try: children = proc.children(recursive=True)
    except: return {}
    stats = {"rss": 0, "vms": 0, "shared": 0, "data": 0, "uss": 0, "pss": 0, "num_fds": 0, "num_threads": 0, "processes": 0, "cpu": 0}
    clds = len(children)
    if clds==0: return stats
    stats['processes'] = clds

    # Step 1: Initialize CPU counters for new PIDs
    current_pids = set()
    for p in children:
        pid = p.pid
        current_pids.add(pid)
        if pid not in cpu_initialized:
            try:
                p.cpu_percent(interval=None)
                cpu_initialized.add(pid)
            except:
                continue

    # Step 2: Sleep once to allow CPU measurement
    sleep(SAMPLE_INTERVAL)

    # Step 3: Collect CPU%, memory, threads, FDs
    for p in children:
        try:
            stats["cpu"] += int(p.cpu_percent(interval=None))
            try:
                mem = p.memory_full_info()
                stats["uss"] += getattr(mem, "uss", 0)
                stats["pss"] += getattr(mem, "pss", 0)
            except:
                mem = p.memory_info()
            for a in ["rss", "vms", "shared", "data"]:
                stats[a] += getattr(mem, a)
            stats["num_threads"] += p.num_threads()
            try:
                stats["num_fds"] += p.num_fds()
            except:
                pass
        except:
            continue

    # Step 4: Cleanup exited PIDs
    cpu_initialized.intersection_update(current_pids)
    return stats

def monitor_stats(p_id, stats_file_name):
    stime = int(time())
    p = psutil.Process(p_id)
    data = []
    while p.is_running():
        stats = update_monitor_stats(p)
        if not stats:
            sleep(SAMPLE_INTERVAL)
            continue
        stats['time'] = int(time()-stime)
        data.append(stats)
    with open(stats_file_name, "w") as sf:
        json_dump(data, sf)
    return

def run_monitor_on_command(command_to_monitor, stats_file_name):
    p = subprocess.Popen(command_to_monitor, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds= True)
    mon_thd = Thread(target=monitor_stats, args=(p.pid, stats_file_name,))
    mon_thd.start()
    stout, sterr = p.communicate() # this blocks until the process is finished
    mon_thd.join() # wait for monitoring thread to write its output
    return p.returncode, stout
