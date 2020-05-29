import logging


class HostManager:
    hostList = []
    availableHosts = []
    allocatedHosts = []

    def __init__(self, hosts):
        self.hostList = hosts
        self.availableHosts = hosts

    def add(self, hostIp):
        self.hostList.append(hostIp)
        self.availableHosts.append(hostIp)

    def del(self, hostIp):
        if self.allocatedHosts.index(hostIp) > 0:
            logging.error(hostIp + " is allocated and cannot be removed.")
            return

        self.hostList.remove(hostIp)
        if self.availableHosts.index(hostIp) > 0:
            self.availableHosts.remove(hostIp)

    def allocate(self, vcpu, memory, disk):
        hostAllocated = self.availableHosts[1]
        self.availableHosts.remove(hostAllocated)
        self.allocatedHosts.append(hostAllocated)

        return hostAllocated

    def deallocate(self, hostIp):
        if self.hostList.index(hostIp) <= 0:
            logging.error(hostIp + " is not registered")
            return

        if self.allocatedHosts.index(hostIp) <= 0:
            logging.error(hostIp + " is not allocated")
            return

        self.allocatedHosts.remove(hostIp)
        self.availableHosts.append(hostIp)
