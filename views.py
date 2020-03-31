from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser

from edgetron.models import Catalog
from edgetron.serializers import CatalogSerializer

import requests


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
def catalog_onboard(request, id):
    """
    On board the catalog
    """
    if request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = CatalogSerializer(data=data)
        if serializer.is_valid():
            try:
                catalog = Catalog.objects.get(pk=id)
            except Catalog.ObjectDoesNotExist():
                return JsonResponse(serializer.errors, status=400)
            send_network_request()
        else:
            return JsonResponse(serializer.errors, status=400)

        return JsonResponse(serializer.data, status=200)


def send_network_request():
    url = "http://127.0.0.1:8000/sona/v2.0/networks"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'name': 'net1',
        'provider:network_type': 'vlan',
        'provider:physical_network': 'public',
        'provider:segmentation_id': 2,
        'provider:tenant_id': 1
    }
    r = requests.put(url, headers=headers, data=payload)