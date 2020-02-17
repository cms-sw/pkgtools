import subprocess
from threading import Thread
import psutil
from json import dump as json_dump
from time import time, sleep

def update_monitor_stats(proc):
    children = []
    try: children = proc.children(recursive=True)
    except: return {}
    stats = {"rss": 0, "vms": 0, "shared": 0, "data": 0, "uss": 0, "pss": 0, "num_fds": 0, "num_threads": 0, "processes": 0, "cpu": 0}
    clds = len(children)
    if clds==0: return stats
    stats['processes'] = clds
    for cld in children:
        try:
            cld.cpu_percent(interval=None)
            sleep(0.1)
            stats['cpu'] += int(cld.cpu_percent(interval=None))
            stats['num_fds'] += cld.num_fds()
            stats['num_threads'] += cld.num_threads()
            mem = None
            try:
                mem   = cld.memory_full_info()
                for a in ["uss", "pss"]: stats[a]+=getattr(mem,a)
            except:
                mem   = cld.memory_info_ex()
            for a in ["rss", "vms", "shared", "data"]: stats[a]+=getattr(mem,a)
        except: pass
    return stats

def monitor_stats(p_id, stats_file_name):
    stime = int(time())
    p = psutil.Process(p_id)
    data = []
    while p.is_running():
        stats = update_monitor_stats(p)
        if not stats: continue
        stats['time'] = int(time()-stime)
        data.append(stats)
        sleep(1.0)
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
