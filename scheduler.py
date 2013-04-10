from Queue import Queue
from threading import Thread
from time import sleep
import threading
import sys
import traceback
from StringIO import StringIO

# Helper class to avoid conflict between result
# codes and quit state transition.
class _SchedulerQuitCommand(object):
  pass

def transition(what, fromList, toList):
  try:
    fromList.remove(what)
  except ValueError, e:
    print what + " not in source list"
    raise e
  toList.append(what)

class Scheduler(object):
  # A simple job scheduler.
  # Workers queue is to specify to threads what to do. Results
  # queue is whatched by the master thread to wait for results
  # of workers computations.
  # All worker threads begin trying to fetch from the command queue (and are
  # therefore blocked).
  # Master thread does the scheduling and then sits waiting for results.
  # Scheduling implies iterating on the list of jobs and creates an entry
  # in the parallel queue for all the jobs which does not have any dependency
  # which is not done.
  # If a job has dependencies which did not build, move it do the failed queue.
  # Post an appropriate build command for all the new jobs which got added.
  # If there are jobs still to be done, post a reschedule job on the command queue
  # if there are no jobs left, post the "kill worker" task.
  # There is one, special, "final-job" which depends on all the scheduled jobs
  # either parallel or serial. This job is guaranteed to be executed last and
  # avoids having deadlocks due to all the queues having been disposed.
  def __init__(self, parallelThreads, logDelegate=None):
    self.workersQueue = Queue()
    self.resultsQueue = Queue()
    self.jobs = {}
    self.pendingJobs = []
    self.runningJobs = []
    self.doneJobs = []
    self.brokenJobs = []
    self.parallelThreads = parallelThreads
    self.logDelegate = logDelegate
    self.errors = {}
    if not logDelegate:
      self.logDelegate = self.__doLog 
    # Add a final job, which will depend on any spawned task so that we do not
    # terminate until we are completely done.
    self.finalJobDeps = []
    self.finalJobSpec = [self.doSerial, "final-job", self.finalJobDeps] + [self.__doLog, "Nothing else to be done, exiting."]
    self.resultsQueue.put((threading.currentThread(), self.finalJobSpec))
    self.jobs["final-job"] = {"scheduler": "serial", "deps": self.finalJobSpec, "spec": self.finalJobSpec}
    self.pendingJobs.append("final-job")

  def run(self):
    for i in xrange(self.parallelThreads):
      t = Thread(target=self.__createWorker())
      t.daemon = True
      t.start()
    
    self.notifyMaster(self.__rescheduleParallel)
    # Wait until all the workers are done.
    while self.parallelThreads:
      try:
        who, item = self.resultsQueue.get()
        #print who, item
        item[0](*item[1:])
        sleep(0.1)
      except KeyboardInterrupt:
        print "Ctrl-c received, waiting for workers to finish"
        while self.workersQueue.full():
          self.workersQueue.get(False)
        self.shout(self.quit)
    
    # Prune the queue.
    while self.resultsQueue.full():
      item = self.resultsQueue.get() 
      item[0](*item[1:])
    return

  # Create a worker.
  def __createWorker(self):
    def worker():
      while True:
        taskId, item = self.workersQueue.get()
        try:
          result = item[0](*item[1:])
        except Exception, e:
          s = StringIO()
          traceback.print_exc(file=s)
          result = s.getvalue()
          
        if type(result) == _SchedulerQuitCommand:
          self.notifyMaster(self.__releaseWorker)
          return
        self.log(str(item) + " done")
        self.notifyMaster(self.__updateJobStatus, taskId, result)
        self.notifyMaster(self.__rescheduleParallel)
        # Only in 2.5: self.workersQueue.task_done()
    return worker
  
  def __releaseWorker(self):
    self.parallelThreads -= 1

  def parallel(self, taskId, deps, *spec):
    if taskId in self.pendingJobs:
      self.log("Double task %s" % taskId)
    self.jobs[taskId] = {"scheduler": "parallel", "deps": deps, "spec":spec}
    self.pendingJobs.append(taskId)
    self.finalJobDeps.append(taskId)

  # Does the rescheduling of tasks. Derived class should call it.
  def __rescheduleParallel(self):
    parallelJobs = [j for j in self.pendingJobs if self.jobs[j]["scheduler"] == "parallel"]
    # First of all clean up the pending parallel jobs from all those
    # which have broken dependencies.
    for taskId in parallelJobs:
      brokenDeps = [dep for dep in self.jobs[taskId]["deps"] if dep in self.brokenJobs]
      if not brokenDeps:
        continue
      transition(taskId, self.pendingJobs, self.brokenJobs)
      self.errors[taskId] = "The following dependencies could not complete:\n%s" % "\n".join(brokenDeps)

    # If no tasks left, quit. Notice we need to check also for serial jobs
    # since they might queue more parallel payloads.
    if not self.pendingJobs:
      self.shout(self.quit)
      self.notifyMaster(self.quit)
      return

    # Otherwise do another round of scheduling of all the tasks. In this
    # case we only queue parallel jobs to the parallel queue.
    for taskId in parallelJobs:
      pendingDeps = [dep for dep in self.jobs[taskId]["deps"] if not dep in self.doneJobs]
      if pendingDeps:
        continue
      # No broken dependencies and no pending ones. we can continue.
      transition(taskId, self.pendingJobs, self.runningJobs)
      self.__scheduleParallel(taskId, self.jobs[taskId]["spec"])

  # Update the job with the result of running.
  def __updateJobStatus(self, taskId, error):
    if not error:
      transition(taskId, self.runningJobs, self.doneJobs)
      return
    transition(taskId, self.runningJobs, self.brokenJobs)
    self.errors[taskId] = error
  
  # One task at the time.
  def __scheduleParallel(self, taskId, commandSpec):
    self.workersQueue.put((taskId, commandSpec))

  # Helper to enqueue commands for all the threads.
  def shout(self, *commandSpec):
    for x in xrange(self.parallelThreads):
      self.__scheduleParallel("quit-" + str(x), commandSpec)

  # Helper to enqueu replies to the master thread.
  def notifyMaster(self, *commandSpec):
    self.resultsQueue.put((threading.currentThread(), commandSpec))

  def serial(self, taskId, deps, *commandSpec):
    spec = [self.doSerial, taskId, deps] + list(commandSpec)
    self.resultsQueue.put((threading.currentThread(), spec))
    self.jobs[taskId] = {"scheduler": "serial", "deps": deps, "spec": spec}
    self.pendingJobs.append(taskId)
    self.finalJobDeps.append(taskId)

  def doSerial(self, taskId, deps, *commandSpec):
    brokenDeps = [dep for dep in deps if dep in self.brokenJobs]
    if brokenDeps:
      transition(taskId, self.pendingJobs, self.brokenJobs)
      self.errors[taskId] = "The following dependencies could not complete:\n%s" % "\n".join(brokenDeps)
      # Remember to do the scheduling again!
      self.notifyMaster(self.__rescheduleParallel)
      return
    
    # Put back the task on the queue, since it has pending dependencies.
    pendingDeps = [dep for dep in deps if not dep in self.doneJobs]
    if pendingDeps:
      self.resultsQueue.put((threading.currentThread(), [self.doSerial, taskId, deps] + list(commandSpec)))
      return
    # No broken dependencies and no pending ones. Run the job.
    transition(taskId, self.pendingJobs, self.runningJobs)
    try:
      result = commandSpec[0](*commandSpec[1:])
    except Exception, e:
      s = StringIO()
      traceback.print_exc(file=s)
      result = s.getvalue()
    self.__updateJobStatus(taskId, result)
    # Remember to do the scheduling again!
    self.notifyMaster(self.__rescheduleParallel)
  
  # Helper method to do logging:
  def log(self, s):
    self.notifyMaster(self.logDelegate, s)

  # Task which forces a worker to quit.
  def quit(self):
    self.log("Requested to quit.")
    return _SchedulerQuitCommand()

  # Helper for printouts.
  def __doLog(self, s):
    print s

  def reschedule(self):
    self.notifyMaster(self.__rescheduleParallel)

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
  scheduler.parallel("download", [], dummyTask)
  scheduler.parallel("build", ["download"], dummyTask)
  scheduler.serial("install", ["build"], dummyTask)

if __name__ == "__main__":
  scheduler = Scheduler(10)
  scheduler.run()

  scheduler = Scheduler(1)
  scheduler.run()
  
  scheduler = Scheduler(10)
  scheduler.parallel("test", [], scheduler.log, "This is england");
  scheduler.run()

  scheduler = Scheduler(10)
  for x in xrange(50):
    scheduler.parallel("test" + str(x), [], dummyTask)
  scheduler.run()
  # Notice we have 51 jobs because there is always a toplevel one
  # which depends on all the others.
  assert(len(scheduler.brokenJobs) == 0)
  assert(len(scheduler.jobs) == 51)
  
  scheduler = Scheduler(1)
  scheduler.parallel("test", [], errorTask)
  scheduler.run()
  # Again, since the toplevel one always depend on all the others
  # it is always broken if something else is brokend.
  assert(len(scheduler.brokenJobs) == 2)
  assert(len(scheduler.runningJobs) == 0)
  assert(len(scheduler.doneJobs) == 0)
  
  # Check dependency actually works.
  scheduler = Scheduler(10)
  scheduler.parallel("test2", ["test1"], dummyTask)
  scheduler.parallel("test1", [], dummyTaskLong) 
  scheduler.run()
  assert(scheduler.doneJobs == ["test1", "test2", "final-job"])

  # Check dependency actually works.
  scheduler = Scheduler(10)
  scheduler.parallel("test3", ["test2"], dummyTask)
  scheduler.parallel("test2", ["test1"], errorTask)
  scheduler.parallel("test1", [], dummyTaskLong) 
  scheduler.run()
  assert(scheduler.doneJobs == ["test1"])
  assert(scheduler.brokenJobs == ["test2", "test3", "final-job"])

  # Check ctrl-C will exit properly.
  scheduler = Scheduler(2)
  for x in xrange(250):
    scheduler.parallel("test" + str(x), [], dummyTask)
  print "Print Control-C to continue"
  scheduler.run()

  # Handle tasks with exceptions.
  scheduler = Scheduler(2)
  scheduler.parallel("test", [], exceptionTask)
  scheduler.run()
  assert(scheduler.errors["test"])

  # Handle tasks which depend on tasks with exceptions.
  scheduler = Scheduler(2)
  scheduler.parallel("test0", [], dummyTask)
  scheduler.parallel("test1", [], exceptionTask)
  scheduler.parallel("test2", ["test1"], dummyTask)
  scheduler.run()
  assert(scheduler.errors["test1"])
  assert(scheduler.errors["test2"])

  # Handle serial execution tasks.
  scheduler = Scheduler(2)
  scheduler.serial("test0", [], dummyTask)
  scheduler.run()
  assert(scheduler.doneJobs == ["test0", "final-job"])

  # Handle serial execution tasks, one depends from
  # the previous one.
  scheduler = Scheduler(2)
  scheduler.serial("test0", [], dummyTask)
  scheduler.serial("test1", ["test0"], dummyTask)
  scheduler.run()
  assert(scheduler.doneJobs == ["test0", "test1", "final-job"])

  # Serial tasks depending on one another.
  scheduler = Scheduler(2)
  scheduler.serial("test1", ["test0"], dummyTask)
  scheduler.serial("test0", [], dummyTask)
  scheduler.run()
  assert(scheduler.doneJobs == ["test0", "test1", "final-job"])

  # Serial and parallel tasks being scheduled at the same time.
  scheduler = Scheduler(2)
  scheduler.serial("test1", ["test0"], dummyTask)
  scheduler.serial("test0", [], dummyTask)
  scheduler.parallel("test2", [], dummyTask)
  scheduler.parallel("test3", [], dummyTask)
  scheduler.run()
  scheduler.doneJobs.sort()
  assert(scheduler.doneJobs == ["final-job", "test0", "test1", "test2", "test3"])

  # Serial and parallel tasks. Parallel depends on serial.
  scheduler = Scheduler(2)
  scheduler.serial("test1", ["test0"], dummyTask)
  scheduler.serial("test0", [], dummyTask)
  scheduler.parallel("test2", ["test1"], dummyTask)
  scheduler.parallel("test3", ["test2"], dummyTask)
  scheduler.run()
  assert(scheduler.doneJobs == ["test0", "test1", "test2", "test3", "final-job"])

  # Serial task scheduling two parallel task and another dependent
  # serial task. This is actually what needs to be done for building 
  # packages. I.e.
  # The first serial task is responsible for checking if a package is already there,
  # then it queues a parallel download sources task, a subsequent build sources
  # one and finally the install built package one.
  scheduler = Scheduler(3)
  scheduler.serial("check-pkg", [], scheduleMore, scheduler)
  scheduler.run()
  assert(scheduler.doneJobs == ["check-pkg", "download", "build", "install", "final-job"])
