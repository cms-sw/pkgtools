
import random
from threading import Lock
class RandomSchedulerTest:
    def __init__(self,
                 scheduler,
                 initial_jobs=100,
                 max_deps=5,
                 dynamic_job_probability=0.1,
                 serial_probability=0.3,
                 failure_probability=0.0,
                 seed=None):

        self.scheduler = scheduler
        self.initial_jobs = initial_jobs
        self.max_deps = max_deps
        self.dynamic_job_probability = dynamic_job_probability
        self.serial_probability = serial_probability
        self.failure_probability = failure_probability
        self.lock = Lock()
        self.counter = 0
        if seed is not None:
            random.seed(seed)

    def _next_job_id(self):
        with self.lock:
            jid = f"job-{self.counter}"
            self.counter += 1
            return jid

    def _task(self, job_id):
        """
        Random task implementation.
        Can:
          - succeed
          - fail
          - dynamically create more jobs
        """
        if random.random() < self.failure_probability:
            return f"{job_id} failed intentionally"
        if random.random() < self.dynamic_job_probability:
            self._create_dynamic_jobs(parent=job_id)
        return ""

    def _create_dynamic_jobs(self, parent):
        """
        Dynamically add 1-3 new jobs.

        New jobs depend on the current completed job,
        therefore no cycle can be introduced.
        """
        num_new = random.randint(1, 3)
        for _ in range(num_new):
            jid = self._next_job_id()
            deps = [parent]
            if random.random() < self.serial_probability:
                self.scheduler.serial(
                    jid,
                    1,
                    deps,
                    self._task,
                    jid
                )
            else:
                self.scheduler.parallel(
                    jid,
                    1,
                    deps,
                    self._task,
                    jid
                )

    def build_initial_graph(self):
        """
        Create an initial random DAG.
        may only depend on jobs < N.
        """
        created = []
        for _ in range(self.initial_jobs):
            jid = self._next_job_id()
            max_possible = min(
                len(created),
                self.max_deps
            )
            ndeps = random.randint(0, max_possible)
            deps = random.sample(created, ndeps)
            if random.random() < self.serial_probability:
                self.scheduler.serial(
                    jid,
                    1,
                    deps,
                    self._task,
                    jid
                )
            else:
                self.scheduler.parallel(
                    jid,
                    1,
                    deps,
                    self._task,
                    jid
                )
            created.append(jid)

    def run(self):
        self.build_initial_graph()
        self.scheduler.run()
