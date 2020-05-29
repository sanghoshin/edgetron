import requests

class SonaHandler
    sona_server_ip = ""
    sona_url = "http://" + sona_server_ip + ":8181/onos/openstacknetworking/"
    sona_headers = {'Content-Type': 'application/json', 'Authorization': 'Basic b25vczpyb2Nrcw=='}

    def __init__(self, sona_ip):
        sona_server_ip = sona_ip

    def create_subnet(self, network_id, subnet_id, tenant_id, cidr, start_ip, end_ip, gateway):
        url = self.sona_url + "subnets"
        payload = {
            "subnet": {
                "id": subnet_id,
                "allocation_pools": [
                    {
                        "start": start_ip,
                        "end": end_ip
                    }
                ],
                "cidr": cidr,
                "host_routes": [],
                "subnetpool_id": "null",
                "enable_dhcp": "true",
                "name": "k8s VM subnet",
                "network_id": network_id,
                "tenant_id": tenant_id,
                "ip_version": 4,
                "cidr": "192.168.199.0/24",
                "gateway_ip": gateway,
            }
        }
        r = requests.post(url, headers=self.sona_headers, json=payload)
        return r


    def create_network(self, network_id, segment_id, tenant_id):
        url = self.sona_url + "networks"
        payload = {
            "network": {
                "status": "ACTIVE",
                "subnets": [],
                "id": network_id,
                "provider:segmentation_id": segment_id,
                "is_default": "false",
                "port_security_enabled": "true",
                "name": "k8s_vm_network",
                "tenant_id": tenant_id,
                "admin_state_up": "true",
                "provider:network_type": "vxlan",
                "mtu": 1450
            }
        }
        r = requests.post(url, headers=self.sona_headers, json=payload)
        return r


    def create_port(self, network_id, subnet_id, port_id, ip_address, tenant_id, mac_address):
        url = self.sona_url + "ports"
        payload = {
            "port": {
                "status": "DOWN",
                "binding:host_id": "",
                "id": port_id,
                "name": "private-port",
                "network_id": network_id,
                "mac_address": mac_address,
                "fixed_ips": [
                    {
                        "subnet_id": subnet_id,
                        "ip_address": ip_address
                    }
                ],
                "tenant_id": tenant_id
            }
        }
        r = requests.post(url, headers=self.sona_headers, json=payload)
        return r
