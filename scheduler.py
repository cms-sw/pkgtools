import sys
from queue import Queue, PriorityQueue, Empty
from io import StringIO
from threading import Thread
from time import sleep
import threading
import traceback
from rmanager import ResourceManager

from enum import Enum

class State(Enum):
  PENDING = 1
  RUNNING = 2
  DONE = 3
  BROKEN = 4

class TaskTypes(Enum):
  SERIAL = 1
  PARALLEL = 2

class Scheduler(object):
  """
  Event-driven dependency scheduler.

  Architecture:
    - The master thread owns all scheduler state.
    - Worker threads execute parallel jobs only.
    - Workers never modify scheduler state directly.
    - Workers communicate with the master via notifyQueue.
    - Dependency completion immediately activates dependent jobs.

  Job lifecycle:

      PENDING
         |
         v
      readyQueue
         |
         v
      RUNNING
       /   \
      v     v
    DONE  BROKEN

  Scheduling priority:
    Lower numeric values indicate higher priority.

  Example:
    priority=1     -> highest priority
    priority=1000  -> lowest priority

  Priorities are typically derived from reverse dependency
  counts so that packages which unlock the largest portion
  of the dependency graph are scheduled first.
  """
  def __init__(self, parallelThreads, logDelegate=None, buildStats=None, parallelDownloads=2, checkCycles=False):
    self.cv = threading.Condition()
    self.checkCycles = checkCycles
    self.executingTasks = 0
    self.shutdownRequested = False

    # Execution queue for parallel jobs.
    #
    # Entries:
    #   (priority, sequence, taskId, callback)
    #
    # Lower priority values are scheduled first.
    # Sequence provides FIFO ordering within equal priorities.
    self.workersQueue = PriorityQueue()

    # Execution queue for serial jobs.
    # Serial jobs run in the master thread and are processed
    # according to scheduler priority.
    #
    # Entries:
    #   (priority, sequence, taskId, callback)
    #
    # Lower priority values are processed first.
    # Sequence provides FIFO ordering within equal priorities.
    self.resultsQueue = PriorityQueue()

    # Thread-safe communication channel from worker threads to the master thread.
    # Workers never modify scheduler state directly.
    # Instead they enqueue notifications which are later
    # executed by the master thread.
    self.notifyQueue = Queue()

    self.readyQueue = Queue()

    # Set of runnable parallel jobs waiting for resource
    # allocation and scheduling.
    #
    # Jobs are first activated into readyQueue.
    # Parallel jobs are then moved into parallelReady where
    # download/build limits and resource manager constraints
    # can be applied before actual scheduling.
    self.parallelReady = set()

    self.jobs = {}
    self.reverseDeps = {}
    self.stateCounter = {}

    # Monotonically increasing sequence number used to
    # preserve FIFO ordering among jobs having identical
    # priorities in PriorityQueue.
    self.jobSequence = 0

    for state in State:
      self.stateCounter[state] = 0
    self.doneJobs = set()
    self.doneOrdered = []
    self.brokenJobs = set()
    self.brokenOrdered = []
    self.parallelThreads = parallelThreads+parallelDownloads
    self.logDelegate = logDelegate
    self.resourceManager = None
    self.reservedJobsCount = {"build": 0, "fetch": 0, "download": 0, "max_build": parallelThreads, "max_download": parallelDownloads}
    self.errors = {}
    self.workers = []
    self.masterThread = threading.current_thread()

    # Synthetic job added during shutdown.
    #
    # Depends on every scheduled job and provides a single
    # aggregate success/failure result for the entire build.
    self.final_job = "final-job"

    self.runtimeError = []
    if not logDelegate:
      self.logDelegate = self.__doLog 
    if buildStats:
      self.resourceManager = ResourceManager(buildStats, self)

  def run(self):
    assert(self.masterThread == threading.current_thread())
    try:
      self.__run()
    finally:
      self.__requestShutdown()
      self.__doNotifications()
      for t in self.workers:
        t.join()
      self.__doNotifications()
      self.__addJob(TaskTypes.SERIAL, self.final_job, 1, list(self.jobs.keys()), False, [])
      self.__setState(self.final_job, State.RUNNING)
      if self.stateCounter[State.BROKEN]:
        self.__setState(self.final_job, State.BROKEN)
      else:
        self.__setState(self.final_job, State.DONE)
      self.__doNotifications()

  def parallel(self, taskId, priority, deps, *spec):
    if threading.current_thread() is not self.masterThread:
      self.notifyMaster(self.parallel, taskId, priority, deps, *spec)
      return
    self.__addJob(TaskTypes.PARALLEL, taskId, priority, deps, True, *spec)

  def serial(self, taskId, priority, deps, *spec):
    if threading.current_thread() is not self.masterThread:
      self.notifyMaster(self.serial, taskId, priority, deps, *spec)
      return
    self.__addJob(TaskTypes.SERIAL, taskId, priority, deps, True, self.__doSerial, taskId, *spec)

  def forceDone(self, taskId):
    if threading.current_thread() is not self.masterThread:
      self.notifyMaster(self.forceDone, taskId)
      return
    self.__addJob(TaskTypes.SERIAL, taskId, 1, [], False, [])
    if self.jobs[taskId]["state"] != State.PENDING: return
    self.__setState(taskId, State.RUNNING)
    self.__updateJobStatus(taskId, "")

  def notifyMaster(self, *commandSpec):
    self.notifyQueue.put((threading.currentThread(), commandSpec))

  # Helper method to do logging:
  def log(self, s, level=0):
    self.notifyMaster(self.logDelegate, s, level)

  def __run(self):
    assert(self.masterThread == threading.current_thread())
    for i in range(self.parallelThreads):
      t = Thread(target=self.__processParallel)
      self.workers.append(t)
      t.start()
    while True:
      self.__doNotifications()
      try:
        pri, seq, taskId, item = self.resultsQueue.get(timeout=0.1)
        item[0](*item[1:])
      except Empty:
        pass
      except KeyboardInterrupt:
        print("Ctrl-C received, shutting down")
        self.__requestShutdown()
      with self.cv:
        if self.shutdownRequested:
          break
        if self.__isQuiescent():
          break
    return

  # Valid transitions:
  #
  #   PENDING -> RUNNING
  #   RUNNING -> DONE
  #   RUNNING -> BROKEN
  #
  # Any other transition indicates a scheduler bug.
  def __setState(self, taskId, new_state):
    assert(self.masterThread == threading.current_thread())
    old = self.jobs[taskId]["state"]
    self.log(f"Changing job state from {old} to {new_state} for {taskId}", 30)
    if old == new_state:
      self.__runtimeError(f"Duplicate transition {old} -> {new_state} for {taskId}")
    if old in (State.DONE, State.BROKEN) or (new_state == State.PENDING):
      self.__runtimeError(f"Illegal transition {old} -> {new_state} for {taskId}")
    self.jobs[taskId]["state"] = new_state
    self.stateCounter[old] -= 1
    self.stateCounter[new_state] += 1
    if (self.jobs[taskId]["scheduler"] == TaskTypes.PARALLEL):
      task_type = self.jobs[taskId]["task_type"]
      if task_type != "force":
        if new_state == State.RUNNING:
          self.reservedJobsCount[task_type] += 1
        elif (old == State.RUNNING) and (new_state in (State.DONE, State.BROKEN)):
          self.reservedJobsCount[task_type] -= 1
    if new_state == State.BROKEN:
      self.brokenOrdered.append(taskId)
      self.brokenJobs.add(taskId)
    elif new_state == State.DONE:
      self.doneOrdered.append(taskId)
      self.doneJobs.add(taskId)

  def __processParallel(self):
    assert(self.masterThread != threading.current_thread())
    while True:
      pri, seq, taskId, item = self.workersQueue.get()
      if taskId == "__QUIT__":
        self.log("Requested to quit. %s" % threading.current_thread())
        return
      with self.cv:
        self.executingTasks += 1
      try:
        result = item[0](*item[1:])
      except Exception as e:
        s = StringIO()
        traceback.print_exc(file=s)
        result = s.getvalue()
      with self.cv:
        self.executingTasks -= 1
        self.cv.notify_all()
      if self.resourceManager and taskId.startswith('build-'):
        self.notifyMaster(self.resourceManager.releaseResourcesForExternal, taskId)
      self.notifyMaster(self.__updateJobStatus, taskId, result)

  def __requestShutdown(self):
    assert(self.masterThread == threading.current_thread())
    with self.cv:
      if self.shutdownRequested:
        return
      self.shutdownRequested = True
    for _ in self.workers:
        self.workersQueue.put((0, 1, "__QUIT__", None))

  def __isQuiescent(self):
    """
    Return True when no more work can be performed.

    The scheduler is quiescent when:
    - no worker is executing a task
    - no jobs are PENDING
    - no jobs are RUNNING
    - no activated jobs are waiting
    - no notifications are pending
    - no serial jobs are pending
    At this point the build graph has fully converged.
    """
    assert(self.masterThread == threading.current_thread())
    return (
        self.executingTasks == 0 and
        self.stateCounter[State.PENDING] == 0 and
        self.stateCounter[State.RUNNING] == 0 and
        self.readyQueue.empty() and
        not self.parallelReady and
        self.notifyQueue.empty() and
        self.resultsQueue.empty()
    )

  def __doNotifications(self):
    assert(self.masterThread == threading.current_thread())
    while True:
      try:
        who, item = self.notifyQueue.get_nowait()
        item[0](*item[1:])
      except Empty:
        break

  def __tryActivate(self, taskId):
    """
    Attempt to activate a pending task.
    A task becomes runnable when:
    - all dependencies exist
    - all dependencies are DONE

    If any dependency is BROKEN then the task and all of its
    downstream dependents are immediately marked BROKEN.

    Successfully activated tasks are inserted into readyQueue.
    """
    assert(self.masterThread == threading.current_thread())
    job = self.jobs[taskId]
    if job["state"] != State.PENDING:
        return
    if job.get("queued", False):
        return
    for d in job["deps"]:
      if d not in self.jobs:
        return
      dep_state = self.jobs[d]["state"]

      # Dependency failure is propagated immediately through
      # the reverse dependency graph so that downstream jobs
      # do not remain pending waiting for a scheduler pass.
      if dep_state == State.BROKEN:
        error = f"Dependency {d} failed."
        stack = [taskId]
        while stack:
          current = stack.pop()
          cjob  = self.jobs.get(current)
          if (not cjob) or (cjob["state"] != State.PENDING):
            continue
          self.__setState(current, State.BROKEN)
          self.errors[current] = error
          stack.extend(self.reverseDeps.get(current, []))
        return
      if dep_state != State.DONE:
        return
    job["queued"] = True
    self.readyQueue.put(taskId)
    self.notifyMaster(self.__dispatchReadyJobs)

  def __wouldCreateCycle(self, taskId, deps):
    assert(self.masterThread == threading.current_thread())
    stack = list(deps)
    visited = set()
    while stack:
      current = stack.pop()
      if current == taskId:
        return True
      if current in visited:
        continue
      visited.add(current)
      if current in self.jobs:
        stack.extend(self.jobs[current]["deps"])
    return False

  def __addJob(self, job_type, taskId, priority, deps, tryActivate, *spec):
    # queued=True means the job has already been activated and
    # inserted into readyQueue. This prevents duplicate activation
    # when multiple dependencies complete at nearly the same time.
    assert(self.masterThread == threading.current_thread())
    if taskId in self.jobs: return
    if taskId != self.final_job:
      if self.final_job in deps:
        self.__runtimeError(f"Task {taskId} should not add dependency on %s" % self.final_job)
      if self.checkCycles and self.__wouldCreateCycle(taskId, deps):
        self.__runtimeError(f"Adding {taskId} would create a dependency cycle")
    job = {"scheduler": job_type, "deps": deps, "state": State.PENDING, "queued": False, "spec": spec, "priority": priority}
    if job_type == TaskTypes.PARALLEL:
      job["task_type"] = "force"
      task_types = taskId.split("-")
      if (len(task_types)>1) and (task_types[0] in ["build", "download", "fetch"]):
        job["task_type"] = task_types[0]
    self.jobs[taskId] = job
    self.stateCounter[State.PENDING] += 1
    if tryActivate:
      for dep in deps:
        self.reverseDeps.setdefault(dep, set()).add(taskId)
      self.__tryActivate(taskId)
 
  def __dispatchReadyJobs(self):
    """
    Dispatch runnable jobs.

    Scheduling policy:
    1. Move activated jobs from readyQueue.
    2. Serial jobs are scheduled immediately.
    3. Parallel jobs are collected in parallelReady.
    4. Download jobs are limited by max_download.
    5. Build jobs are limited by max_build.
    6. ResourceManager may further restrict which
       build jobs can run.
    7. Eligible jobs are scheduled in priority order.
    """
    assert(self.masterThread == threading.current_thread())
    ready = []
    while True:
      try:
        taskId = self.readyQueue.get_nowait()
        ready.append(taskId)
      except Empty:
         break
    if not ready and not self.parallelReady:
        return
    for taskId in ready:
      job = self.jobs[taskId]
      if job["state"] != State.PENDING:
        continue
      if job["scheduler"] == TaskTypes.SERIAL:
        self.__scheduleJob(taskId)
      else:
        self.parallelReady.add(taskId)
    if not self.parallelReady:
      return

    buildJobs =[]
    downloadJobs = []
    forceJobs = []
    bldCount = self.reservedJobsCount["max_build"]-self.reservedJobsCount["build"]
    dwnCount = self.reservedJobsCount["max_download"]-self.reservedJobsCount["download"]
    # Sort by scheduler priority.
    #
    # Lower numeric values indicate higher priority.
    # Jobs with identical priorities preserve scheduling
    # order through the sequence number assigned when
    # they are queued for execution.
    for taskId in sorted(self.parallelReady, key=lambda tid: self.jobs[tid].get("priority", 1)):
      job = self.jobs[taskId]
      taskType = job["task_type"]
      if taskType == "download":
        if dwnCount>0:
          downloadJobs.append(taskId)
          dwnCount -= 1
      elif taskType == "build":
        if bldCount>0: #include all build jobs so that we can match those which can be run
          buildJobs.append(taskId)
      else:
        forceJobs.append(taskId)
    if bldCount>0 and buildJobs:
      if self.resourceManager:
        buildJobs = self.resourceManager.allocResourcesForExternals(buildJobs, count=bldCount)
      else:
        buildJobs = buildJobs[:bldCount]
    for taskId in forceJobs + downloadJobs + buildJobs:
      self.parallelReady.remove(taskId)
      self.__scheduleJob(taskId)

  def __updateJobStatus(self, taskId, error):
    assert(self.masterThread == threading.current_thread())
    if not error:
      self.log(f"{taskId} done")
      self.__setState(taskId, State.DONE)
    else:
      self.log(f"{taskId} failed.\n{error}")
      self.__setState(taskId, State.BROKEN)
      self.errors[taskId] = error
    for depTask in self.reverseDeps.get(taskId, set()):
      if self.jobs[depTask]["state"] != State.PENDING:
        continue
      self.__tryActivate(depTask)
    self.reverseDeps.pop(taskId, None)
    self.notifyMaster(self.__dispatchReadyJobs)
  
  def __scheduleJob(self, taskId):
    assert(self.masterThread == threading.current_thread())
    job = self.jobs[taskId]
    self.__setState(taskId, State.RUNNING)
    self.jobSequence +=  1
    if job["scheduler"] == TaskTypes.SERIAL:
      self.resultsQueue.put((job["priority"], self.jobSequence, taskId, job["spec"]))
    else:
      self.workersQueue.put((job["priority"], self.jobSequence, taskId, job["spec"]))

  def __doSerial(self, taskId, *commandSpec):
    assert(self.masterThread == threading.current_thread())
    self.log(f"Running serial job {taskId}", 30)
    brokenDeps = [dep for dep in self.jobs[taskId]["deps"]  if self.jobs[dep]["state"] == State.BROKEN]
    result = ""
    if brokenDeps:
      result = "The following dependencies could not complete:\n%s" % "\n".join(brokenDeps)
    else:
      try:
        result = commandSpec[0](*commandSpec[1:])
      except Exception as e:
        s = StringIO()
        traceback.print_exc(file=s)
        result = s.getvalue()
    self.__updateJobStatus(taskId, result)
 
  def __runtimeError(self, error):
    assert(threading.current_thread() == self.masterThread)
    raise RuntimeError(error)

  # Helper for printouts.
  def __doLog(self, s, level=0):
    print (s)

def forceDone(scheduler, idx):
  if idx == 50:
    for i in range(51,100):
      scheduler.log(f"Force done dep-{i}")
      scheduler.forceDone(f"dep-{i}")
  return

def dummyTask():
  sleep(0.1)

def dummyTaskLong():
  sleep(1)

def errorTask():
  return "This will always have an error"

def exceptionTask():
  raise Exception("foo")

# Mimics cmsBuild workflow.
def scheduleMore(scheduler):
  scheduler.parallel("download-file", 1, [], dummyTask)
  scheduler.parallel("build-test", 1, ["download-file"], dummyTask)
  scheduler.serial("install", 1, ["build-test"], dummyTask)

def run_test(scheduler, skip_run=False):
  print("Starting test ...")
  if not skip_run:
    scheduler.run()
  print("Done test")
  print("Checking tests results ...")
  if scheduler.stateCounter[State.BROKEN]:
    assert(len(scheduler.brokenOrdered)>=1)
    assert(scheduler.brokenOrdered[-1] == scheduler.final_job)
  elif scheduler.stateCounter[State.DONE]:
    assert(len(scheduler.doneOrdered)>=1)
    assert(scheduler.doneOrdered[-1] == scheduler.final_job)
  assert(scheduler.stateCounter[State.BROKEN]+scheduler.stateCounter[State.DONE] ==
         len(scheduler.brokenOrdered)+len(scheduler.doneOrdered))
  for state in [State.PENDING, State.RUNNING]:
    if scheduler.stateCounter[state] != 0:
      print(scheduler.stateCounter)
      all_jobs = list(scheduler.jobs.keys())
      print("Total Jobs:", len(all_jobs))
      for j in scheduler.jobs:
        if scheduler.jobs[j]["state"] == State.PENDING:
          print("JOB  %s %s %s" % (j , scheduler.jobs[j]["scheduler"], scheduler.jobs[j]["state"]))
          for dep in scheduler.jobs[j]["deps"]:
            print("  DEP: %s %s %s" % (dep, scheduler.jobs[j]["scheduler"], scheduler.jobs[dep]["state"]))
    assert(scheduler.stateCounter[state]==0)
  for item in scheduler.reservedJobsCount.keys():
    if item.startswith("max_"):
      continue
    assert(scheduler.reservedJobsCount[item]==0)
  for task_id, job in scheduler.jobs.items():
    for dep in job.get("deps", []):
        if scheduler.jobs[dep]["state"] == State.DONE:
            assert(dep in scheduler.doneJobs)
            assert(dep in scheduler.doneOrdered)
  for task_id in scheduler.doneJobs:
    for dep in scheduler.jobs[task_id]["deps"]:
        assert(dep in scheduler.doneJobs)
        assert(dep in scheduler.doneOrdered)
  all_jobs = set(scheduler.jobs.keys())
  assert all(
    scheduler.jobs[j]["state"] in (State.DONE, State.BROKEN)
    for j in all_jobs
  )
  print("Default checks passed")

def test_RandomSchedulerTest():
  from test_scheduler import RandomSchedulerTest
  scheduler = Scheduler(10)
  test = RandomSchedulerTest(
    scheduler,
    initial_jobs=4000,
    max_deps=50,
    dynamic_job_probability=0.5,
    serial_probability=0.2,
    failure_probability=0.01,
    seed=12345
  )
  test.run()
  print("Done:", scheduler.stateCounter[State.DONE])
  print("Broken:", scheduler.stateCounter[State.BROKEN])
  run_test(scheduler, True)

if __name__ == "__main__":
  scheduler = Scheduler(10)
  run_test(scheduler)

  scheduler = Scheduler(1)
  run_test(scheduler)

  scheduler = Scheduler(10)
  scheduler.parallel("test", 1, [], scheduler.log, "This is england");
  run_test(scheduler)

  scheduler = Scheduler(1)
  for x in range(10):
    scheduler.parallel("test", 1, [], dummyTask)
    scheduler.serial("test", 1, [], dummyTask)
  run_test(scheduler)
  assert(scheduler.stateCounter[State.BROKEN] == 0)
  assert(len(scheduler.jobs) == 2)

  scheduler = Scheduler(8)
  for i in range(100):
    if i % 2:
      scheduler.forceDone(f"dep-{i}")
    else:
      scheduler.parallel(f"dep-{i}", 1, [], dummyTask)
  scheduler.parallel("final", 1, [f"dep-{i}" for i in range(100)],dummyTask)
  run_test(scheduler)

  scheduler = Scheduler(8)
  taskOrder = []
  for i in range(100):
    scheduler.parallel(f"dep-{i}", 1, ["dep-%s" % (i+1)], dummyTask)
    taskOrder.insert(0, f"dep-{i}")
  scheduler.parallel("dep-100", 1, [], dummyTask)
  taskOrder.insert(0, "dep-100")
  taskOrder.append(scheduler.final_job)
  run_test(scheduler)
  assert(scheduler.doneOrdered == taskOrder)

  scheduler = Scheduler(8)
  tasks = set()
  for i in range(100):
    tasks.add(f"dep-{i}")
    scheduler.parallel(f"dep-{i}", 1, [], forceDone, scheduler, i)
  tasks.add(scheduler.final_job)
  run_test(scheduler)
  assert(scheduler.doneJobs == tasks)

  scheduler = Scheduler(8)
  taskOrder = []
  for i in range(100):
    taskOrder.insert(0, f"dep-{i}")
    scheduler.parallel(taskOrder[0], 1000-i, [], forceDone, scheduler, i)
  taskOrder.append(scheduler.final_job)
  run_test(scheduler)
  assert(scheduler.doneOrdered == taskOrder)

  scheduler = Scheduler(1)
  for x in range(10):
    scheduler.parallel("test", 1, [], dummyTask)
    scheduler.serial("test", 1, [], dummyTask)
  run_test(scheduler)
  assert(scheduler.stateCounter[State.BROKEN] == 0)
  assert(len(scheduler.jobs) == 2)

  scheduler = Scheduler(10)
  for x in range(50):
    scheduler.parallel("test" + str(x), 1, [], dummyTask)
  run_test(scheduler)
  assert(scheduler.stateCounter[State.BROKEN] == 0)
  assert(len(scheduler.jobs) == 51)

  scheduler = Scheduler(1)
  scheduler.parallel("test", 1, [], errorTask)
  run_test(scheduler)
  # Again, since the toplevel one always depend on all the others
  # it is always broken if something else is brokend.
  assert(scheduler.stateCounter[State.BROKEN] == 2)
  assert(scheduler.stateCounter[State.DONE] == 0)

  # Check dependency actually works.
  scheduler = Scheduler(10)
  scheduler.parallel("test2", 1, ["test1"], dummyTask)
  scheduler.parallel("test1", 1, [], dummyTaskLong)
  run_test(scheduler)
  assert(scheduler.doneOrdered == ["test1", "test2", scheduler.final_job])

  # Check dependency actually works.
  scheduler = Scheduler(10)
  scheduler.parallel("build-test3", 1, ["build-test2"], dummyTask)
  scheduler.parallel("build-test2", 1, ["build-test1"], errorTask)
  scheduler.parallel("build-test1", 1, [], dummyTaskLong)
  run_test(scheduler)
  assert(scheduler.doneOrdered == ["build-test1"])
  assert(scheduler.brokenOrdered == ["build-test2", "build-test3", scheduler.final_job])

  # Check ctrl-C will exit properly.
  scheduler = Scheduler(2)
  doneOrdered = ["build-test" + str(x) for x in range(250)]
  for x in doneOrdered:
    scheduler.parallel(x, 1, [], dummyTask)
  print ("Print Control-C to continue")
  run_test(scheduler)
  doneOrdered.append(scheduler.final_job)
  assert(scheduler.stateCounter[State.DONE] == len(doneOrdered))
  assert(scheduler.doneJobs == set(doneOrdered))

  scheduler = Scheduler(16)
  for x in range(250):
    scheduler.parallel("test" + str(x), 1, [], dummyTask)
  print ("Print Control-C to continue")
  run_test(scheduler)

  scheduler = Scheduler(2)
  doneOrdered = ["test" + str(x) for x in range(250)]
  for x in doneOrdered:
    scheduler.serial(x, 1, [], dummyTask)
  run_test(scheduler)
  doneOrdered.append(scheduler.final_job)
  assert(scheduler.stateCounter[State.DONE] == len(doneOrdered))
  assert(scheduler.doneJobs == set(doneOrdered))
  assert(scheduler.doneOrdered == doneOrdered)

  # Handle tasks with exceptions.
  scheduler = Scheduler(2)
  scheduler.parallel("build-test", 1, [], exceptionTask)
  run_test(scheduler)
  assert(scheduler.errors["build-test"])

  # Handle tasks which depend on tasks with exceptions.
  scheduler = Scheduler(2)
  scheduler.parallel("build-test0", 1, [], dummyTask)
  scheduler.parallel("build-test1", 1, [], exceptionTask)
  scheduler.parallel("build-test2", 1, ["build-test1"], dummyTask)
  run_test(scheduler)
  assert(scheduler.errors["build-test1"])
  assert(scheduler.errors["build-test2"])

  # Handle serial execution tasks.
  scheduler = Scheduler(2)
  scheduler.serial("test0", 1, [], dummyTask)
  run_test(scheduler)
  assert(scheduler.doneOrdered == ["test0", scheduler.final_job])

  # Handle serial execution tasks, one depends from
  # the previous one.
  scheduler = Scheduler(2)
  scheduler.serial("test0", 1, [], dummyTask)
  scheduler.serial("test1", 1, ["test0"], dummyTask)
  run_test(scheduler)
  assert(scheduler.doneOrdered == ["test0", "test1", scheduler.final_job])

  # Serial tasks depending on one another.
  scheduler = Scheduler(2)
  scheduler.serial("test1", 1, ["test0"], dummyTask)
  scheduler.serial("test0", 1, [], dummyTask)
  run_test(scheduler)
  assert(scheduler.doneOrdered == ["test0", "test1", scheduler.final_job])

  # Serial and parallel tasks being scheduled at the same time.
  scheduler = Scheduler(2)
  scheduler.serial("test1", 1, ["test0"], dummyTask)
  scheduler.serial("test0", 1, [], dummyTask)
  scheduler.parallel("build-test2", 1, [], dummyTask)
  scheduler.parallel("build-test3", 1, [], dummyTask)
  run_test(scheduler)
  scheduler.doneOrdered.sort()
  doneOrdered = ["build-test2", "build-test3", scheduler.final_job, "test0", "test1"]
  assert(scheduler.doneOrdered == doneOrdered)
  assert(scheduler.stateCounter[State.DONE] == len(doneOrdered))

  # Serial and parallel tasks. Parallel depends on serial.
  scheduler = Scheduler(2)
  scheduler.serial("test1", 1, ["test0"], dummyTask)
  scheduler.serial("test0", 1, [], dummyTask)
  scheduler.parallel("build-test2", 1, ["test1"], dummyTask)
  scheduler.parallel("build-test3", 1, ["build-test2"], dummyTask)
  run_test(scheduler)
  assert(scheduler.doneOrdered == ["test0", "test1", "build-test2", "build-test3", scheduler.final_job])

  # Serial task scheduling two parallel task and another dependent
  # serial task. This is actually what needs to be done for building 
  # packages. I.e.
  # The first serial task is responsible for checking if a package is already there,
  # then it queues a parallel download sources task, a subsequent build sources
  # one and finally the install built package one.
  scheduler = Scheduler(3)
  scheduler.serial("check-pkg", 1, [], scheduleMore, scheduler)
  run_test(scheduler)
  assert(scheduler.doneOrdered == ["check-pkg", "download-file", "build-test", "install", scheduler.final_job])

  test_RandomSchedulerTest()
