class ResourceManager(object):
    def __init__(self, ESstats, cpu_percent_usage, memory_percent_usage, njobs):
        self.machineResources = { "total": {"cpu_75": cpu_percent_usage*int(ESstats["MachineCPUCount"]), 
                                            "rss_75" : memory_percent_usage*int(ESstats["MachineMemoryGB"])*10737418 },
                                  "available": {"cpu_75": cpu_percent_usage*int(ESstats["MachineCPUCount"]),
                                            "rss_75" : memory_percent_usage*int(ESstats["MachineMemoryGB"])*10737418 } }
        self.externalsStats = ESstats["externals"]# this should be get before running pkgtools
        self.resourcesAllocatedForExternals = {} # resources that were alocated for given externals, say root -> "root": {"rss":"", cpu:""}
        self.jobsOrderMetric = "cpu_75" # default to cpu
        self.missingExternalsStrategy = None # runFirst, runLast
    
    def allocResourcesForExternals(self, externalsList=[]): # return ordered list for externals that can be started
        # first, strip the names from build-*++version and make a tmp name to full name dict.
        # toolfiles should not arrive here, but will also work if they do
        ext_name_to_fullname_dict = {}
        for e in externalsList:
            short_name = e.split('+')[1]
            ext_name_to_fullname_dict[short_name]=e
        externalsList_shortNames = ext_name_to_fullname_dict.keys()
        # if record for an external is not available, allocate it 1/4th of the resources and run it first
        # OR allocate all resources for each missing external, forcing them to build last one by one.
        externals_to_run = []
        for ext in externalsList_shortNames:
            if ext not in self.externalsStats:
                # external is not found, this should happen only for new externals. get the first element whichever it is and change its properties
                self.externalsStats[ext] = [{"name":ext, "cpu_75":self.machineResources["total"]["cpu_75"]/4,"rss_75":self.machineResources["total"]["rss_75"]/10 }]
            externals_to_run.append(self.externalsStats[ext][0])        
        # first order them by metric and then run over to alloc resources
        externalsList_sorted = [ext for ext in sorted(externals_to_run, key=lambda x: x[self.jobsOrderMetric], reverse=True)]

        externals_to_run = []
        for ex_stats in externalsList_sorted:
            if (ex_stats["cpu_75"]<=self.machineResources["available"]["cpu_75"] and ex_stats["rss_75"]<=self.machineResources["available"]["rss_75"]):
                self.resourcesAllocatedForExternals[ex_stats["name"]] = {}
                for prm in ["rss_75", "cpu_75"]:
                    self.machineResources["available"][prm] -= ex_stats[prm]
                    self.resourcesAllocatedForExternals[ex_stats["name"]][prm] = ex_stats[prm]
                externals_to_run.append(ext_name_to_fullname_dict[ex_stats["name"]]) # this gets the full names
        return externals_to_run

    def releaseResourcesForExternal(self, external): # external name
        # get the external name only
        external = external.split('+')[1]
        for prm in ["rss_75", "cpu_75"]:
            self.machineResources["available"][prm] += self.resourcesAllocatedForExternals[external][prm]
        del self.resourcesAllocatedForExternals[external]
