class IpManager:
    ipAllocations = {}
    vm_subnet = ""
    bootstrap_subnet = ""

    def __init__(self, vm_subnet, bootstrap_subnet):
        self.vm_subnet = vm_subnet
        self.bootstrap_subnet = bootstrap_subnet

    def allocate_ip(self, port_id):
        for ip in range(1, 255):
            if self.ipAllocations[ip] == '':
                self.ipAllocation[ip] = port_id
                ip_address = self.vm_subnet + "." + str(ip)
                return ip_address
        return ""

    def get_bootstrap_nw_ip(self, port_id):
        for ip in range(1, 255):
            if self.ipAllocations[ip] == '':
                self.ipAllocation[ip] = port_id
                ip_address = self.vm_subnet + "." + str(ip)
                return ip_address
        return ""



