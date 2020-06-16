import requests


class SonaHandler:
    def __init__(self, sona_ip):
        self.sona_headers = {'Content-Type': 'application/json', 'Authorization': 'Basic b25vczpyb2Nrcw=='}
        self.sona_server_ip = sona_ip
        self.sona_url = "http://" + self.sona_server_ip + ":8181/onos/openstacknetworking/"

    def create_subnet(self, subnet):
        url = self.sona_url + "subnets"
        payload = {
            "subnet": {
                "id": subnet.subnetId,
                "cidr": subnet.cidr,
                "host_routes": [],
                "subnetpool_id": "null",
                "enable_dhcp": "true",
                "name": "k8s VM subnet",
                "network_id": subnet.networkId,
                "tenant_id": subnet.tenantId,
                "ip_version": 4
            }
        }
        r = requests.post(url, headers=self.sona_headers, json=payload)
        return r

    def create_network(self, network):
        url = self.sona_url + "networks"
        payload = {
            "network": {
                "status": "ACTIVE",
                "subnets": [],
                "id": network.networkId,
                "provider:segmentation_id": network.segmentId,
                "is_default": "false",
                "port_security_enabled": "true",
                "name": "k8s_vm_network",
                "tenant_id": network.tenantId,
                "admin_state_up": "true",
                "provider:network_type": "vxlan",
                "mtu": 1450
            }
        }
        r = requests.post(url, headers=self.sona_headers, json=payload)
        return r

    def create_port(self, port):
        url = self.sona_url + "ports"
        payload = {
            "port": {
                "status": "DOWN",
                "binding:host_id": "",
                "id": port.portId,
                "name": "private-port",
                "network_id": port.networkId,
                "mac_address": port.macAddress,
                "fixed_ips": [
                    {
                        "subnet_id": port.subnetId,
                        "ip_address": port.ipAddress
                    }
                ],
                "tenant_id": port.tenantId
            }
        }
        r = requests.post(url, headers=self.sona_headers, json=payload)
        return r
