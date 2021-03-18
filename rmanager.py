import re
class ResourceManager(object):
    def __init__(self, ESstats, scheduler, highestPriortyOnly = False):
        self.esStats = ESstats
        self.scheduler = scheduler
        self.machineResources = ESstats["resources"]
        self.resouceList = ["cpu", "rss"]
        self.allocated = {}
        self.highestPriortyOnly = highestPriortyOnly
        self.priorityList = ["time"] # can be any list from the stat keys
    
    def allocResourcesForExternals(self, externalsList, count=1000): # return ordered list for externals that can be started
        externals_to_run = []
        if count<=0: return externals_to_run
        for ext_full in externalsList:
            stats = {"name": ext_full}
            ext = ext_full.split('+')[1]
            if ext not in self.esStats["packages"]:
                idx = -1
                for exp in self.esStats["known"]:
                    if re.match(exp[0], ext):
                        idx = exp[1]
                        break
                for k in self.esStats["defaults"]:
                    stats[k] = self.esStats["defaults"][k][idx]
                self.scheduler.log("New external found, creating default entry %s" % stats)
            else:
                for k in self.esStats["defaults"]:
                    stats[k] = self.esStats["packages"][ext][k]
            externals_to_run.append(stats)
        # first order them by metric and then run over to alloc resources
        externalsList_sorted = [ext for ext in sorted(externals_to_run, key=lambda x: tuple(x[k] for k in self.priorityList), reverse=True)]
        externals_ordered = []
        for ex_stats in externalsList_sorted:
            if not [r for r in self.resouceList if ex_stats[r]>self.machineResources[r]]:
                for prm in self.resouceList:
                    self.machineResources[prm] -= ex_stats[prm]
                externals_ordered.append(ex_stats["name"])
                self.allocated[ex_stats["name"]] = ex_stats
                self.scheduler.log("Allocating resouces %s" % ex_stats)
                count-=1
                if count<=0:
                  break
            elif self.highestPriortyOnly:
              break
        self.scheduler.log("Available resouces %s" % self.machineResources)
        return externals_ordered

    def releaseResourcesForExternal(self, external):
        if external not in self.allocated: return
        for prm in self.resouceList:
            self.machineResources[prm] +=  self.allocated[external][prm]
        self.scheduler.log("Released resources: %s , %s" % (self.allocated[external], self.machineResources))
        del self.allocated[external]
