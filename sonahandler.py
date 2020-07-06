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
                "id": subnet.subnet_id,
                "cidr": subnet.cidr,
                "host_routes": [],
                "subnetpool_id": "null",
                "enable_dhcp": "true",
                "name": "k8s VM subnet",
                "network_id": subnet.network_id,
                "tenant_id": subnet.tenant_id,
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
                "id": network.network_id,
                "provider:segmentation_id": network.segment_id,
                "is_default": "false",
                "port_security_enabled": "true",
                "name": "k8s_vm_network",
                "tenant_id": network.tenant_id,
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
                "id": port.port_id,
                "name": "private-port",
                "network_id": port.network_id,
                "mac_address": port.mac_address,
                "fixed_ips": [
                    {
                        "subnet_id": port.subnet_id,
                        "ip_address": port.ip_address
                    }
                ],
                "tenant_id": port.tenant_id
            }
        }
        r = requests.post(url, headers=self.sona_headers, json=payload)
        return r
