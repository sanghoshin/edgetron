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
            r = send_network_request(network_id)
            if r.status_code != 201:
                return JsonResponse(r.text, safe=False)
            subnet_id = str(uuid.uuid4())
            r = send_subnet_request(network_id, subnet_id)
            if r.status_code != 201:
                return JsonResponse(r.text, safe=False)
            r = send_createport_request()
            if r.status_code != 201:
                return JsonResponse(r.text, safe=False)
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


def send_subnet_request(network_id, subnet_id):
    url = sona_url + "subnets"
    payload = {
        "subnet": {
            "id": subnet_id,
            "network_id": network_id,
            "ip_version": 4,
            "cidr": "192.168.199.0/24"
        }
    }
    r = requests.post(url, headers=sona_headers, json=payload)
    return r


def send_network_request(network_id):
    url = sona_url + "networks"
    payload = {
        "network": {
            "id": network_id,
            "name": "sample_network",
            "admin_state_up": "true",
            "dns_domain": "my-domain.org",
            "mtu": 1400
        }
    }
    r = requests.post(url, headers=sona_headers, json=payload)
    return r


def send_createport_request():
    url = sona_url + "ports"
    payload = {
        "port": {
            "id": str(uuid.uuid4()),
            "name": "private-port",
            "network_id": "a87cc70a-3e15-4acf-8205-9b711a3531b7",
            "fixed_ips": [
                {
                    "ip_address": "12.12.11.12"
                }
            ],
            "tenant_id": 1
        }
    }
    r = requests.post(url, headers=sona_headers, json=payload)
    return r
