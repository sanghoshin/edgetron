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
                "gateway": subnet.cidr[:-4] + "1",
                "subnetpool_id": "null",
                "enable_dhcp": "true",
                "name": subnet.name,
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
                "name": network.name,
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
                "status": "ACTIVE",
                "binding:host_id": "",
                "id": port.port_id,
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

    def delete_port(self, port):
        url = self.sona_url + "ports/" + port.port_id
        r = requests.delete(url, headers=self.sona_headers)
        return r

    def delete_network(self, network):
        url = self.sona_url + "networks/" + network.network_id
        r = requests.delete(url, headers=self.sona_headers)
        return r

    def delete_subnet(self, subnet):
        url = self.sona_url + "subnets/" + subnet.subnet_id
        r = requests.delete(url, headers=self.sona_headers)
        return r