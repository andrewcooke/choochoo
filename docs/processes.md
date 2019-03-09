
need to run pipelines in parallel.

* unify pipelines:
  * make path a karg
  * make start and finish kargs, replacing after logic

* implement multi processing:
  * add --worker flag
  * change pipeline class to return list of missing times
  * add max number of threads to pipeline (or cost?)
  * add max number of threads to constants
  * if possible threads > 1 and not worker, spawn processes with date ranges
    * another cost calculation here to decide chunking
  * track processes
  * if database locked, retry
  * remove lock testing for --worker
  * add retry etc for acquire_lock
  