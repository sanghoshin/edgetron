class IpManager:
    ipAllocations = {}
    subnet = ""

    def __init__(self, subnet):
        self.subnet = subnet[:len(subnet)-4]
        for ip in range(100, 255):
            self.ipAllocations[ip] = ''

    def allocate_ip(self, cluster_id):
        for ip in range(100, 255):
            if self.ipAllocations[ip] == '':
                self.ipAllocations[ip] = cluster_id
                ip_address = self.subnet + str(ip)
                return ip_address
        return ""

    def get_master_ip(self, cluster_id):
        for ip in range(100, 255):
            if self.ipAllocations[ip] == cluster_id:
                ip_address = self.subnet + str(ip)
                return ip_address
        # only for test
        return self.subnet + "100"