from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser

from edgetron.models import K8sCatalog, SonaNetwork, SonaSubnet, SonaPort
from edgetron.serializers import K8sCatalogSerializer
from edgetron.sonahandler import SonaHandler
from edgetron.hostmanager import HostManager
from edgetron.ipmanager import IpManager

import uuid, random, subprocess, logging, sys, threading, time

# cluster library path needs to be added through configuration
sys.path.append("./cluster-api-lib")

from cluster_api import *

from machine import Machine
from machineset import MachineSet
from cluster import Cluster
from network import Network

# The following values need to be set from MEPM configuration
sona_ip = "10.2.1.33"
host_list = ["10.2.1.68", "10.2.1.69", "10.2.1.70"]
flat_network_cidr = "10.10.10.0/24"
vm_network_cidr = "10.10.1.0/24"
flat_network_id = str(uuid.uuid4())

host_manager = HostManager(host_list)


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
    sona = SonaHandler(sona_ip)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = K8sCatalogSerializer(data=data)
        if serializer.is_valid():
            serializer.save()

            # Create a virtual network and subnet using SONA
            vm_network = SonaNetwork(clusterId=serializer.clusterId,
                                     networkId=str(uuid.uuid4()),
                                     segmentId=1,
                                     tenantId=str(uuid.uuid4()))
            vm_network.save()
            r = sona.create_network(vm_network)
            if r.status_code != 201:
                return JsonResponse(r.text, safe=False)

            subnet = SonaSubnet(networkId=vm_network.networkId,
                                subnetId=str(uuid.uuid4()),
                                tenantId=vm_network.tenantId,
                                cidr=vm_network_cidr)
            subnet.save()
            r = sona.create_subnet(subnet)
            if r.status_code != 201:
                return JsonResponse(r.text, safe=False)

            # Extract variables from MEPM REST Call
            vcpus = serializer.vcpus
            memory = serializer.memory
            storage = serializer.storage
            host_ip = host_manager.allocate(vm_network.clusterId, vcpus, memory, storage)
            k8s_version = serializer.version
            image_name = serializer.image

            # Create a cluster
            cluster = Cluster()
            cluster.withClusterName(vm_network.clusterId) \
                .withKubeVersion(k8s_version) \
                .withOsDistro(image_name)

            cluster_yaml = create_cluster_yaml(cluster)
            # create_cluster(cluster_yaml)
            logging.info(cluster_yaml)

            # Define flat and default network
            flat_net = Network(vm_network.networkId)
            flat_net.withSubnet(flat_network_cidr)
            default_net = Network(flat_network_id)
            default_net.withSubnet(vm_network_cidr) \
                .setPrimary(True)

            # Create a master node
            master = Machine()
            master.withCluster(cluster) \
                .withMachineType("master") \
                .withVcpuNum(vcpus) \
                .withMemorySize(memory) \
                .withDiskSize(storage) \
                .withHostIpaddress(host_ip) \
                .appendNet(flat_net) \
                .appendNet(default_net) \
                .withCniName("sona-pt") \
                .appendCniOption("onos-ip", sona_ip)

            master_yaml = create_machine_yaml(master)
            # create_machine(master_yaml)
            logging.info(master_yaml)

            # Create a worker set
            worker_set = MachineSet(5)
            worker_set.withCluster(cluster) \
                .withMachineType("worker") \
                .withVcpuNum(vcpus) \
                .withMemorySize(memory) \
                .withDiskSize(storage) \
                .withHostIpaddress(host_ip) \
                .appendNet(flat_net) \
                .appendNet(default_net) \
                .withUseDpdk(True) \
                .withCniName("sona-pt") \
                .appendCniOption("onos-ip", sona_ip)

            worker_set_yaml = create_machine_set_yaml(worker_set)
            # create_machineset(worker_set_yaml)
            logging.info(worker_set_yaml)

            check_cluster_status(sona, subnet)

        else:
            return JsonResponse(serializer.errors, status=400)

        return JsonResponse(serializer.data, status=200)


@csrf_exempt
def deployment_application(request, cid, chartid):
    """""
    Deploy Application
    """""
    try:
        catalog = K8sCatalog.objects.get(pk=cid)
    except K8sCatalog.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = K8sCatalogSerializer(data=data)
        if serializer.is_valid():
            chart_path = get_chart_path(chartid)
            host_ip = host_manager.get_host_ip(cid)
            deploy(host_ip, chart_path)
        else:
            return JsonResponse(serializer.errors, status=400)

        return JsonResponse(serializer.data, status=200)


def get_chart_path(chart_id):
    """ Originally chart path needs to be extracted from DB
        using the chart_id """
    return "bitnami/nginx"


def deploy(host_ip, chart_path):
    command = "helm install my-release " + chart_path

    ssh = subprocess.Popen(["ssh", "%s" % host_ip, command],
                           shell=False,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    result = ssh.stdout.readlines()
    if not result:
        error = ssh.stderr.readlines()
        logging.debug(error)
    else:
        logging.info(result)

def check_cluster_status(sona, subnet):

    # need to check the status continuously until it returns
    # the correct status

    cluster_status_temp = {
        "mectb-test-master":{
            "state":"Running",
            "networks":[
                {
                    "interfaceName":"tap4b923054b50",
                    "ipAddress":"192.168.200.51",
                    "macAddress":"06:b3:7c:58:21:b6",
                    "networkName":"flat-net"
                }
            ],
            "id":"7e053658-9886-4828-a41d-fcb68c2e3d28"
        },
        "mectb-test-worker-set-6m8pf":{
            "state":"Running",
            "networks":[
                {
                    "interfaceName":"tape5873f89c38",
                    "ipAddress":"192.168.200.3",
                    "macAddress":"06:73:8d:d7:a9:e2",
                    "networkName":"flat-net"
                }
            ],
            "id":"a9dc320e-d320-4c18-831a-b839b8d3087c"
        },
        "mectb-test-worker-set-qrgwc":{
            "state":"Running",
            "networks":[
                {
                    "interfaceName":"tap03f4fd95a91",
                    "ipAddress":"192.168.200.2",
                    "macAddress":"06:21:63:25:25:3f",
                    "networkName":"flat-net"
                }
            ],
            "id":"2d0e47b6-1e51-41b8-b8bd-e91bcd442cf6"
        }
    }

    cluster_status = {}
    all_status = "PROCESSING"
    while all_status != "COMPLETE":
        time.sleep(1)
        # cluster_status = get_cluster_status(cluster_id)
        # logging.info(status)
        all_status = "COMPLETE"
        for machine, status in cluster_status_temp.items():
            state = status['state']
            logging.info("state : " + state)
            if state != "Running":
                all_status = "PROCESSING"
        logging.info("Check thread: status is " + all_status)


    for machine, status in cluster_status_temp.items():
        machine_name = machine
        state = status['state']
        vm_id = status['id']
        networks = status['networks']
        for network in networks:
            mac = network['macAddress']
            ip = network['ipAddress']
            intf = network['interfaceName']
            name = network['networkName']
            #port_id = intf[3:]
            port_id = str(uuid.uuid4())

            port = SonaPort(portId=port_id,
                            subnetId=subnet.subnetId,
                            networkId=subnet.networkId,
                            tenantId=subnet.tenantId,
                            ipAddress=ip,
                            macAddress=mac)
            port.save()

            r = sona.create_port(port)
            if r.status_code != 201:
                logging.error("SONA create port error!")
