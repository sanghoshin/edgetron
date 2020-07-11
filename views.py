from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser

from edgetron.models import K8sCatalog, SonaNetwork, SonaSubnet, SonaPort
from edgetron.serializers import K8sCatalogSerializer, AppCatalogSerializer
from edgetron.sonahandler import SonaHandler
from edgetron.hostmanager import HostManager
from edgetron.ipmanager import IpManager

import uuid, random, subprocess, logging, sys, threading, time, json

# cluster library path needs to be added through configuration
sys.path.append("./cluster-api-lib")
logging.basicConfig(filename="./edgetron.log", level=logging.INFO)

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
            vm_network = SonaNetwork(cluster_id=serializer.cluster_id,
                                     network_id=str(uuid.uuid4()),
                                     segment_id=1,
                                     tenant_id=str(uuid.uuid4()))
            vm_network.save()
            r = sona.create_network(vm_network)
            if r.status_code != 201:
                return JsonResponse(r.text, safe=False)

            subnet = SonaSubnet(network_id=vm_network.network_id,
                                subnet_id=str(uuid.uuid4()),
                                tenant_id=vm_network.tenant_id,
                                cidr=vm_network_cidr)
            subnet.save()
            r = sona.create_subnet(subnet)
            if r.status_code != 201:
                return JsonResponse(r.text, safe=False)

            # Extract variables from MEPM REST Call
            vcpus = serializer.vcpus
            memory = serializer.memory
            storage = serializer.storage
            host_ip = host_manager.allocate(vm_network.cluster_id, vcpus, memory, storage)
            k8s_version = serializer.version
            image_name = serializer.image
            nodes = serializer.scaling.init

            # Create a cluster
            cluster = Cluster()
            cluster.withClusterName(vm_network.cluster_id) \
                .withKubeVersion(k8s_version) \
                .withServiceDomain("mectb.io") \
                .withOsDistro(image_name) \
                .withHelmVersion("3.0")

            cluster_yaml = create_cluster_yaml(cluster)
            logging.info(cluster_yaml)
            create_cluster(cluster_yaml)

            # Define flat and default network
            flat_network_ip = ip_manager.allocate_ip(vm_network.cluster_id)
            flat_net = Network(vm_network.network_id)
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

            check_cluster_status(sona, subnet, vm_network.cluster_id)

        else:
            return JsonResponse(serializer.errors, status=400)

        response = {"cluster_id": serializer.cluster_id}
        return JsonResponse(json.dumps(response), status=200, safe=False)

    elif request.method == 'GET':
        cluster_info_response = get_cluster_info()
        return cluster_info_response


@csrf_exempt
def kubernetes_cluster_info(request, cid):
    if request.method == 'GET':
        try:
            logging.info("Cluster info detail for " + cid)
            cluster = K8sCatalog.objects.get(cluster_id=cid)
        except K8sCatalog.DoesNoExist:
            logging.error("Not found!!")
            return HttpResponse(status=404)

        cluster_info = {"cluster_id": cluster.cluster_id}
        vm_info_list = []
        k8s_info_list = []
        cluster_status = get_cluster_status(cid)
        for machine, status in cluster_status.items():
            machine_name = machine
            vm_status = status['vm']
            kube_status = status['kube']
            vm_state = vm_status['state']
            networks = vm_status['networks']
            kube_state = kube_status['state']

            vm_info = {"name" : machine, "status": vm_state}
            vm_info_list.append(json.dumps(vm_info))

            k8s_info = {"node_name": machine, "status": kube_state}
            k8s_info_list.append(json.dumps(k8s_info))

            helm_status = get_helm_status(cid)

        response = {"cluster_id": cid, "vm": vm_info_list, "kubernetes": k8s_info_list,
                    "helm": helm_status}

        return JsonResponse(response, safe=False)

    return HttpResponse(status=400)


def get_application_info_detail(cid):
    try:
        app = ApplicationCatalog.objects.get(cluster_id=cid)
    except ApplicationCatalog.DoesNotExist:
        return HttpResponse(status=404)

    app_info = {"cluster_id": app.cluster_name}
    app_info["name"] = app.application_name
    app_info["status"] = "Running"

    # Need to extract from kubernetes cluster
    pod_info = {"pod": "edgetron-deployment-5f6d596747-7xnk4"}
    pod_info["ready"] = "1/1"
    pod_info["status"] = "Running"
    pod_info["restarts"] = "0"
    pod_info["age"] = "100s"

    app_info_list = []
    app_info_list.append(pod_info)

    app_info["pod_status"] = app_info_list

    return


@csrf_exempt
def deployment(request):

    if request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = AppCatalogSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            chart = serializer.chart
            repo = serializer.repository
            master_vm_ip = ip_manager.get_master_ip(serializer.cluster_id)

            command = "helm install " + serializer.application_name + " " + chart.name
            command_to_add_repo = "helm repo add " + repo.name + " " + repo.url
            key_file = "id_rsa_k8s"
            no_prompt = "-o StrictHostKeyChecking no"
            host_access = "kubernetes@" + master_vm_ip

            ssh_output = subprocess.check_output(["ssh", "-i", key_file, no_prompt, host_access, command_to_add_repo],
                                                 stdin=None, stderr=None, universal_newlines=False, shell=False)
            logging.info(ssh_output)

            ssh_output = subprocess.check_output(["ssh", "-i", key_file, no_prompt, host_access, command],
                                          stdin=None, stderr=None, shell=False, universal_newlines=False)
            logging.info(ssh_output)
        else:
            logging.error("serializer is not valid")
            return JsonResponse(serializer.data, status=400)

        return JsonResponse(serializer.data, status=200)

    elif request.method == 'GET':
        app_info_response = get_application_info()
        return app_info_response

    return JsonResponse(status=400)


def check_cluster_status(sona, subnet, cluster_id):

    cluster_status = {}
    all_status = "PROCESSING"
    while all_status != "COMPLETE":
        time.sleep(1)
        cluster_status = get_cluster_status(cluster_id)
        logging.info(cluster_status)
        all_status = "COMPLETE"
        for machine, status in cluster_status.items():
            vm_status = status['vm']
            state = vm_status['state']
            logging.info("state : " + state)
            if state != "Running":
                all_status = "PROCESSING"

    cluster_status = get_cluster_status(cluster_id)
    for machine, status in cluster_status.items():
        machine_name = machine
        vm_status = status['vm']
        kube_status = status['kube']
        vm_state = vm_status['state']
        networks = vm_status['networks']
        kube_state = kube_status['state']
        kube_info = kube_status['info']

        for network in networks:
            mac = network['macAddress']
            ip = network['ipAddress']
            intf = network['interfaceName']
            name = network['networkName']
            port_id = intf[3:]
            # port_id = str(uuid.uuid4())

            port = SonaPort(port_id=port_id,
                            subnet_id=subnet.subnet_id,
                            network_id=subnet.network_id,
                            tenant_id=subnet.tenant_id,
                            ip_address=ip,
                            mac_address=mac)
            port.save()

            r = sona.create_port(port)
            if r.status_code != 201:
                logging.error("SONA create port error!")

        kube_version = "N/A"
        if kube_info and kube_info.kubelet_version is not None:
            kube_version = kube_info.kubelet_version

        ipaddresses = []
        for network in networks:
            ipaddresses.append(network['ipAddress'])


def get_cluster_info():
    clusters = K8sCatalog.objects.all()
    cluster_info = []
    for cluster in clusters:
        cluster_item = {cluster.cluster_id: cluster.name}
        cluster_info.append(json.dumps(cluster_item))

    return JsonResponse(cluster_info, safe=False)


def get_application_info():
    apps = ApplicationCatalog.objects.all()
    app_info = []
    for app in apps:
        app_item = {apps.cluster_id: apps.application_name}
        app_info.append(json.dumps(app_item))

    return JsonResponse(app_info, safe=False)


def get_helm_status(cid):

    master_vm_ip = ip_manager.get_master_ip(cid)
    command = "helm list"
    key_file = "id_rsa_k8s"
    no_prompt = "-o StrictHostKeyChecking no"
    host_access = "kubernetes@" + master_vm_ip

    try:
        ssh_output = subprocess.check_output(["ssh", "-i", key_file, no_prompt, host_access, command],
                                         stdin=None, stderr=None, universal_newlines=False, shell=False)
    except:
        return "Not Ready"

    logging.info(ssh_output)

    return ssh_output
