from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser

from edgetron.models import Catalog
from edgetron.serializers import CatalogSerializer

import requests

sona_server_IP = "10.2.1.33"
sona_url = "http://" + sona_server_IP + ":8181/onos/openstacknetworking/"
sona_headers = {'Content-Type': 'application/json', 'Authorization': 'Basic b25vczpyb2Nrcw=='}

@csrf_exempt
def catalog_list(request):
    """
    List all code catalogs, or create a new catalog.
    """
    if request.method == 'GET':
        catalogs = Catalog.objects.all()
        serializer = CatalogSerializer(catalogs, many=True)
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = CatalogSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)


@csrf_exempt
def catalog_onboard(request, pk):
    """
    On board the catalog
    """
    try:
        catalog = Catalog.objects.get(pk=pk)
    except Catalog.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = CatalogSerializer(data=data)
        if serializer.is_valid():
            send_network_request()
        else:
            return JsonResponse(serializer.errors, status=400)

        return JsonResponse(serializer.data, status=200)


@csrf_exempt
def application_instantiate(request, pk):
    """""
    Instantiate Application
    """""
    try:
        catalog = Catalog.objects.get(pk=pk)
    except Catalog.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = CatalogSerializer(data=data)
        if serializer.is_valid():
            send_createport_request()
        else:
            return JsonResponse(serializer.errors, status=400)

        return JsonResponse(serializer.data, status=200)


def send_network_request():
    url = sona_url + "networks"
    payload = {
        'name': 'net1',
        'provider:network_type': 'vlan',
        'provider:physical_network': 'public',
        'provider:segmentation_id': 2,
        'provider:tenant_id': 1
    }
    r = requests.put(url, headers=sona_headers, data=payload)


def send_createport_request():
    url = sona_url + "ports"
    payload = {
        "port": {
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
    r = requests.put(url, headers=sona_headers, data=payload)
