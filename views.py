from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser

from edgetron.models import K8sCatalog, SonaNetwork, SonaSubnet, SonaPort
from edgetron.serializers import K8sCatalogSerializer
from edgetron.sonahandler import SonaHandler
from edgetron.hostmanager import HostManager
from edgetron.ipmanager import IpManager

import uuid, random, subprocess, logging, sys

sys.path.append("/home/ubuntu/mysite/cluster-api-lib")

from cluster_api import *

from machine import Machine
from machineset import MachineSet
from cluster import Cluster
from network import Network


sona_ip = "10.2.1.33"
host_list = ["10.2.1.68", "10.2.1.69", "10.2.1.70"]
host_manager = HostManager(host_list)
ip_manager = IpManager("10.10.1", "192.168.0")
flat_network_id = str(uuid.uuid4()) # Need to be configured
flat_network_cidr = "10.10.10.0/24" # Need to be configured


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

            cluster_id = serializer.clusterId
            network_id = str(uuid.uuid4())
            segment_id = 1
            tenant_id = str(uuid.uuid4())
            vm_network = SonaNetwork(clusterId=cluster_id, networkId=network_id, segmentId=segment_id,
                              tenantId=tenant_id)
            vm_network.save()

            r = sona.create_network(vm_network)
            if r.status_code != 201:
                return JsonResponse(r.text, safe=False)

            subnet_id = str(uuid.uuid4())
            cidr = "10.10.1.0/24"
            start = "10.10.1.2"
            end = "10.10.1.255"
            gateway = "10.10.1.1"
            subnet = SonaSubnet(networkId=network_id, subnetId=subnet_id,
                            tenantId=tenant_id, cidr=cidr, startIp=start,
                            endIp=end, gateway=gateway)
            subnet.save()

            r = sona.create_subnet(subnet)
            if r.status_code != 201:
                return JsonResponse(r.text, safe=False)

            port_id = str(uuid.uuid4())
            ip_address = "10.10.1.2"
            mac_data = [0x00, 0x16, 0x3e,
                        random.randint(0x00, 0x7f),
                        random.randint(0x00, 0xff),
                        random.randint(0x00, 0xff)]
            mac_address = ':'.join(map(lambda x: "%02x" % x, mac_data))
            port = SonaPort(portId=port_id, subnetId=subnet_id, networkId=network_id,
                        tenantId=tenant_id, ipAddress=ip_address, macAddress=mac_address)
            port.save()


            # Create a cluster
            cluster = Cluster()
            cluster.withClusterName(cluster_id)
            .withKubeVersion(k8s_version) \
                .withOsDistro(image_name)

            cluster_yaml = create_cluster_yaml(cluster)
            # create_cluster(cluster_yaml)
            logging.info(cluster_yaml)

            # Define flat and default network
            flat_net = Network(network_id)
            flat_net.withSubnet(flat_network_cidr)
            default_net = Network(flat_network_id)
            default_net.withSubnet(cidr) \
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

            #status = get_cluster_status(cluster_id)
            #logging.info(status)


            r = sona.create_port(network_id, subnet_id, port_id, ip_address, tenant_id, mac_address)
            if r.status_code != 201:
                return JsonResponse(r.text, safe=False)

            cluster_id = serializer.clusterId
            vcpus = serializer.vcpus
            memory = serializer.memory
            storage = serializer.storage
            host_ip = host_manager.allocate(cluster_id, vcpus, memory, storage)
            k8s_version = serializer.version
            image_name = serializer.image
            vm_ip = ip_manager.allocate_ip(port_id)
            bootstrap_nw_ip = ip_manager.get_bootstrap_nw_ip(port_id)




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