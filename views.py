from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser

from edgetron.models import K8sCatalog
from edgetron.serializers import K8sCatalogSerializer

import requests, uuid

sona_server_IP = "10.2.1.33"
sona_url = "http://" + sona_server_IP + ":8181/onos/openstacknetworking/"
sona_headers = {'Content-Type': 'application/json', 'Authorization': 'Basic b25vczpyb2Nrcw=='}

@csrf_exempt
def catalog_list(request):
    """
    List all code catalogs, or create a new catalog.
    """
    if request.method == 'GET':
        catalogs = K8sCatalog.objects.all()
        serializer = K8sCatalogSerializer(catalogs, many=True)
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = K8sCatalogSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)


@csrf_exempt
def kubernetes_cluster(request):
    """
    On board the catalog
    """

    if request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = K8sCatalogSerializer(data=data)
        if serializer.is_valid():

            network_id = str(uuid.uuid4())
            segment_id = 1
            tenant_id = str(uuid.uuid4())
            r = send_network_request(network_id, segment_id, tenant_id)
            if r.status_code != 201:
                return JsonResponse(r.text, safe=False)

            subnet_id = str(uuid.uuid4())
            cidr = "10.10.1.0/24"
            start = "10.10.1.2"
            end = "10.10.1.255"
            gateway = "10.10.1.1"
            r = send_subnet_request(network_id, subnet_id, tenant_id, cidr, start, end, gateway)
            if r.status_code != 201:
                return JsonResponse(r.text, safe=False)

            port_id = str(uuid.uuid4())
            ip_address = "10.10.1.2"
            # r = send_createport_request(network_id, port_id, ip_address, tenant_id)
            # if r.status_code != 201:
            #    return JsonResponse(r.text, safe=False)
        else:
            return JsonResponse(serializer.errors, status=400)

        return JsonResponse(serializer.data, status=200)


@csrf_exempt
def deployment_application(request, pk):
    """""
    Deploy Application
    """""
    try:
        catalog = K8sCatalog.objects.get(pk=pk)
    except K8sCatalog.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = K8sCatalogSerializer(data=data)
        if serializer.is_valid():
            r = send_createport_request()
            if r.status_code != 200:
                return JsonResponse(r.text, safe=False)
        else:
            return JsonResponse(serializer.errors, status=400)

        return JsonResponse(serializer.data, status=200)


def send_subnet_request(network_id, subnet_id, tenant_id, cidr, start_ip, end_ip, gateway):
    url = sona_url + "subnets"
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
    r = requests.post(url, headers=sona_headers, json=payload)
    return r


def send_network_request(network_id, segment_id, tenant_id):
    url = sona_url + "networks"
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
    r = requests.post(url, headers=sona_headers, json=payload)
    return r


def send_createport_request(nework_id, port_id, ip_address, tenant_id):
    url = sona_url + "ports"
    payload = {
        "port": {
            "id": port_id,
            "name": "private-port",
            "network_id": nework_id,
            "fixed_ips": [
                {
                    "ip_address": ip_address
                }
            ],
            "tenant_id": tenant_id
        }
    }
    r = requests.post(url, headers=sona_headers, json=payload)
    return r
