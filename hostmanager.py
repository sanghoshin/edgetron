import logging


class HostManager:
    hostAllocations = {}

    def __init__(self, hosts):
        for item in hosts:
            self.hostAllocations.add(item, [])

    def add_host(self, hostIp):
        self.hostAllocations[hostIp] = []

    def del_host(self, hostIp):
        cid_list = self.hostAllocations[hostIp]
        if len(cid_list) > 0:
            logging.error(hostIp + " is not empty and cannot be removed")
            return

        self.hostApplications.pop(hostIp)

    def allocate(self, cid, vcpu, memory, disk):
        host = self.allocate_host(vcpu, memory, disk)
        self.hostAllocations[host].append(cid)

        return host

    def deallocate(self, cid):
        for cid_list in self.hostAllocations.items():
            if cid in cid_list:
                cid_list.remove(cid)
                return

        logging.error(cid + " is not allocated and cannot deallocate it")
        return

    def allocate_host(self, vcpu, memory, disk):
        max = 0
        for cid_list in self.hostAllocations.items():
            size = len(cid_list)
            if max < size:
                max = size

        for hostIp in self.hostAllocations.keys():
            if len(self.hostAllocations[hostIp]) < max:
                return hostIp

        return self.hostAllocations[0]

    def get_host_ip(self, cid):
        for host_ip in self.hostAllocations.keys():
            cid_list = self.hostAllocations[host_ip]
            if cid in cid_list:
                return host_ip
        return ""
