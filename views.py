from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser

from edgetron.models import K8sCatalog, SonaNetwork, SonaSubnet, SonaPort
from edgetron.serializers import K8sCatalogSerializer
from edgetron.sonahandler import SonaHandler
from edgetron.hostmanager import HostManager
from edgetron.ipmanager import IpManager

import uuid, random, subprocess, logging, sys, threading, time, json

# cluster library path needs to be added through configuration
sys.path.append("./cluster-api-lib")
logging.basicConfig(filename="./edgetro.log", level=logging.INFO)

from cluster_api import *

from machine import Machine
from machineset import MachineSet
from cluster import Cluster
from network import Network

# The following values need to be set from MEPM configuration
sona_ip = "192.168.0.236"
host_list = ["192.168.0.236"]
flat_network_cidr = "192.168.200.0/24"
vm_network_cidr = "10.10.1.0/24"
flat_network_id = str(uuid.uuid4())

host_manager = HostManager(host_list)
ip_manager = IpManager(flat_network_cidr)


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
            nodes = serializer.scaling.init

            # Create a cluster
            cluster = Cluster()
            cluster.withClusterName(vm_network.clusterId) \
                .withKubeVersion(k8s_version) \
                .withServiceDomain("mectb.io") \
                .withOsDistro(image_name) \
                .withHelmVersion("3.0")

            cluster_yaml = create_cluster_yaml(cluster)
            logging.info(cluster_yaml)
            create_cluster(cluster_yaml)

            # Define flat and default network
            flat_network_ip = ip_manager.allocate_ip(vm_network.clusterId)
            flat_net = Network(vm_network.networkId)
            flat_net.withSubnet(flat_network_cidr) \
                    .withIpAddress(flat_network_ip) \
                    .setPrimary(True)

            default_net = Network(flat_network_id)
            default_net.withSubnet(vm_network_cidr) \
                .setPrimary(False)

            # Create a master node
            master = Machine()
            master.withCluster(cluster) \
                .withMachineType("master") \
                .withVcpuNum(vcpus) \
                .withMemorySize(memory) \
                .withDiskSize(storage) \
                .withHostIpaddress(host_ip) \
                .appendNet(flat_net) \
                .withCniName("calico") \
                .appendCniOption("onos-ip", sona_ip)

            master_yaml = create_machine_yaml(master)
            create_machine(master_yaml)
            logging.info(master_yaml)

            # Create a worker set
            worker_set = MachineSet(nodes)
            worker_set.withCluster(cluster) \
                .withMachineType("worker") \
                .withVcpuNum(vcpus) \
                .withMemorySize(memory) \
                .withDiskSize(storage) \
                .withHostIpaddress(host_ip) \
                .appendNet(flat_net) \
                .appendNet(default_net) \
                .withCniName("calico") \
                .appendCniOption("onos-ip", sona_ip)

            worker_set_yaml = create_machine_set_yaml(worker_set)
            create_machineset(worker_set_yaml)
            logging.info(worker_set_yaml)

            check_cluster_status(sona, subnet, vm_network.clusterId)

        else:
            return JsonResponse(serializer.errors, status=400)

        return JsonResponse(serializer.data, status=200)
    elif request.method == 'GET':
        cluster_info_response = get_cluster_info()
        return cluster_info_response



@csrf_exempt
def deployment_application(request, cid, chartid):
    """""
    Deploy Application
    """""

    logging.info("Deploy app " + chartid + " in cluster " + cid)

    try:
        clusterId = str(cid)
        catalog = K8sCatalog.objects.get(clusterId=clusterId)
    except K8sCatalog.DoesNotExist:
        logging.error("Cannot find cluster with clusterId " + clusterId)
        return HttpResponse(status=400)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = K8sCatalogSerializer(data=data)
        if serializer.is_valid():
            chart_path = get_chart_path(chartid)
            # Originally, we need to logon to the host and master VM again
            # for installation of application.
            #host_ip = host_manager.get_host_ip(cid)
            master_vm_ip = ip_manager.get_master_ip(cid)
            deploy(master_vm_ip, chart_path)
        else:
            return JsonResponse(serializer.errors, status=400)

        return JsonResponse(serializer.data, status=200)


def get_chart_path(chart_id):
    """ Originally chart path needs to be extracted from DB
        using the chart_id """
    return "bitnami/nginx"


def deploy(host_ip, chart_path):
    command = "helm install my-release " + chart_path
    key_file = "/home/sdn/.ssh/id_rsa_k8s"
    host_access = "kubernetes@" + host_ip

    ssh = subprocess.call(["ssh", "-i", key_file, host_access, command],
                           shell=False,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    if ssh != 0:
        logging.error("Failed to depoly the application")
    else:
        logging.info("The application is deployed successfully")


def check_cluster_status(sona, subnet, cluster_id):
    # need to check the status continuously until it returns
    # the correct status

    cluster_status_temp = {
        "mectb-test-master": {
            "state": "Running",
            "networks": [
                {
                    "interfaceName": "tap4b923054b50",
                    "ipAddress": "192.168.200.51",
                    "macAddress": "06:b3:7c:58:21:b6",
                    "networkName": "flat-net"
                }
            ],
            "id": "7e053658-9886-4828-a41d-fcb68c2e3d28"
        },
        "mectb-test-worker-set-6m8pf": {
            "state": "Running",
            "networks": [
                {
                    "interfaceName": "tape5873f89c38",
                    "ipAddress": "192.168.200.3",
                    "macAddress": "06:73:8d:d7:a9:e2",
                    "networkName": "flat-net"
                }
            ],
            "id": "a9dc320e-d320-4c18-831a-b839b8d3087c"
        },
        "mectb-test-worker-set-qrgwc": {
            "state": "Running",
            "networks": [
                {
                    "interfaceName": "tap03f4fd95a91",
                    "ipAddress": "192.168.200.2",
                    "macAddress": "06:21:63:25:25:3f",
                    "networkName": "flat-net"
                }
            ],
            "id": "2d0e47b6-1e51-41b8-b8bd-e91bcd442cf6"
        }
    }

    cluster_status = {}
    all_status = "PROCESSING"
    while all_status != "COMPLETE":
        time.sleep(1)
        cluster_status = get_cluster_status(cluster_id)
        logging.info(cluster_status)
        all_status = "COMPLETE"
        for machine, status in cluster_status.items():
            state = status['state']
            logging.info("state : " + state)
            if state != "Running":
                all_status = "PROCESSING"

    for machine, status in cluster_status.items():
        machine_name = machine
        state = status['state']
        vm_id = status['id']
        networks = status['networks']
        for network in networks:
            mac = network['macAddress']
            ip = network['ipAddress']
            intf = network['interfaceName']
            name = network['networkName']
            port_id = intf[3:]
            # port_id = str(uuid.uuid4())

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


def get_cluster_info():
    clusters = K8sCatalog.objects.all()
    cluster_info = []
    for cluster in clusters:
        cluster_item = {cluster.clusterId: cluster.name}
        cluster_info.append(json.dumps(cluster_item))

    return JsonResponse(cluster_info, safe=False)
