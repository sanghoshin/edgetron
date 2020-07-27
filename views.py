from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser

from edgetron.models import K8sCatalog, SonaNetwork, SonaSubnet, SonaPort, ApplicationCatalog
from edgetron.serializers import K8sCatalogSerializer, AppCatalogSerializer
from edgetron.sonahandler import SonaHandler
from edgetron.hostmanager import HostManager
from edgetron.ipmanager import IpManager

import uuid, random, subprocess, logging, sys, threading, time, json

# cluster library path needs to be added through configuration
sys.path.append("./cluster-api/core")
logging.basicConfig(filename="./edgetron.log", level=logging.INFO)

from cluster_api import *

from machine import Machine
from machineset import MachineSet
from cluster import Cluster
from network import Network

# The following values need to be set from MEPM configuration
sona_ip = "192.168.0.244"
host_list = ["192.168.0.244"]
flat_network_cidr = "172.16.230.0/24"
flat_network_name = "k8s_flat_network"
flat_subnet_name = "k8s flat subnet"
vm_network_cidr = "10.10.1.0/24"
flat_network_id = "9e9e4325-ee38-4adf-9f86-fb99eaeb2bb6"
flat_subnet_id = "e3f45f0e-130b-4890-a6c8-8c410875e824"
os_image_list = ["ubuntu-1804", "centos-7"]
k8s_ver_list = ["1.17.0"]
master_vcpus = 4
master_storage = 20
master_memory = 8

host_manager = HostManager(host_list)
ip_manager = IpManager(flat_network_cidr)


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

            # Flat network needs to be created only once,
            # but for now we try to create it everytime.
            # result = create_flat_network(sona)
            # if not result:
            #    return HttpResponse(status=500)

            # Create a virtual network and subnet using SONA
            network_id = str(uuid.uuid1())
            vm_network = SonaNetwork(cluster_id=serializer.cluster_id,
                                     network_id=network_id,
                                     segment_id=1,
                                     name="vnet_" + network_id[:10],
                                     tenant_id=str(uuid.uuid1()))
            vm_subnet = SonaSubnet(network_id=vm_network.network_id,
                                subnet_id=str(uuid.uuid1()),
                                tenant_id=vm_network.tenant_id,
                                name="subnet_" + network_id[:10],
                                cidr=vm_network_cidr)
            result = create_sona_network(sona, vm_network, vm_subnet)
            if not result:
                logging.error("Error in creating SONA network or subnet")
                serializer.delete()
                return HttpResponse(status=500)
            vm_network.save()
            vm_subnet.save()

            # Create cluster using cluster API
            create_cluster(serializer, vm_network.cluster_id)

            wait_until_vm_is_created(vm_network.cluster_id)

            result = create_sona_ports(sona, vm_subnet, vm_network.cluster_id)
            if not result:
                logging.error("Error in creating SONA ports")
                delete_cluster(vm_network.cluster_id)
                vm_subnet.delete()
                vm_network.delete()
                serializer.delete()
                return HttpResponse(status=500)
        else:
            return JsonResponse(serializer.errors, status=400)

        dashboard_url = get_dashboard_url(serializer.interfaces.ip_address)
        response = {"cluster_id": serializer.cluster_id, "dashboard_url": dashboard_url}
        return JsonResponse(response, status=200, safe=False)

    elif request.method == 'GET':
        cluster_info_response = get_cluster_info()
        return cluster_info_response


@csrf_exempt
def kubernetes_cluster_info(request, cid):
    if request.method == 'GET':
        try:
            logging.info("Cluster info detail for " + cid)
            cluster = K8sCatalog.objects.get(cluster_id=cid)
        except K8sCatalog.DoesNotExist:
            logging.error("Not found!!")
            return HttpResponse(status=404)

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

            vm_info = {"name": machine, "status": vm_state}
            vm_info_list.append(json.dumps(vm_info))

            k8s_info = {"node_name": machine, "status": kube_state}
            k8s_info_list.append(json.dumps(k8s_info))

        logging.info("check helm status!!")
        helm_status = {"status": get_helm_status(cluster_status)}

        dashboard_url = get_dashboard_url(cluster.interfaces.ip_address)

        response = {"cluster_id": cid, "dashboard_url": dashboard_url, "vm": vm_info_list, "kubernetes": k8s_info_list, "helm": helm_status}

        return JsonResponse(response, safe=False)

    elif request.method == "DELETE":
        remove_cluster(cid)
        response = {"cluster_id": cid}
        return JsonResponse(response, status=200)

    return HttpResponse(status=400)


@csrf_exempt
def application_detail(request, cid):
    try:
        app = ApplicationCatalog.objects.get(cluster_id=cid)
    except ApplicationCatalog.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
        response = get_application_detail(cid, app.application_name)
        return JsonResponse(response, safe=False)
    elif request.method == 'DELETE':
        result = deploy_chart(cid, app.application_name, chart="", mode="uninstall")
        if result:
            app.delete()
            response = {"cluster_id": cid}
            return JsonResponse(response, safe=False)
        else:
            return HttpResponse(status=500)
    else:
        return HttpResponse(status=400)


@csrf_exempt
def deployment(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = AppCatalogSerializer(data=data)
        logging.info(serializer)
        if serializer.is_valid():
            serializer.save()
        else:
            logging.error("serializer is not valid")
            return JsonResponse(serializer.data, status=400)

        app = ApplicationCatalog.objects.filter(cluster_id=serializer.cluster_id)[0]
        logging.info(app)
        charts = app.charts.all()
        repos = app.repositories.all()
        for repo in repos:
            logging.info(repo)
            set_repository(serializer.cluster_id, repo)
        for chart in charts:
            logging.info(chart)
            deploy_chart(serializer.cluster_id, app.application_name, chart, mode="install")

        response = {"cluster_id": serializer.cluster_id}
        return JsonResponse(response, status=200)

    elif request.method == 'GET':
        app_info_response = get_application_info()
        return app_info_response

    return JsonResponse(status=400)


@csrf_exempt
def clean_up_all(request):
    if request.method == 'POST':
        clusters = K8sCatalog.objects.all()
        for cluster in clusters:
            remove_cluster(cluster.cluster_id)

        # Just in case there are dangling SONA data
        nets = SonaNetwork.objects.all()
        for net in nets:
            r = remove_network_data(net.cluster_id)
            if not r:
                return HttpResponse(status=500)

    return HttpResponse(status=200)


def create_cluster(cluster_info, cluster_id):
    # Extract variables from MEPM REST Call
    vcpus = cluster_info.vcpus
    memory = cluster_info.memory
    storage = cluster_info.storage
    host_ip = host_manager.allocate(cluster_id, vcpus, memory, storage)
    k8s_version = cluster_info.version
    image_name = cluster_info.image
    nodes = cluster_info.scaling.current

    # Create a cluster
    cluster = Cluster()
    cluster.withClusterName(cluster_id) \
        .withKubeVersion(k8s_version) \
        .withServiceDomain("mectb.io") \
        .withOsDistro(image_name) \
        .withHelmVersion("3.0")

    cluster_yaml = create_cluster_yaml(cluster)
    logging.info(cluster_yaml)
    create_cluster(cluster_yaml)

    # Define flat and default network
    flat_network_ip = ip_manager.allocate_ip(cluster_id)
    flat_net = Network(flat_network_id)
    flat_net.withSubnet(flat_network_cidr) \
        .setPrimary(True)

    default_net = Network(network_id)
    default_net.withSubnet(vm_network_cidr) \
        .setAddressOverlap(True) \
        .setPrimary(False)

    # Create a master node
    master = Machine()
    master.withCluster(cluster) \
        .withMachineType("master") \
        .withVcpuNum(master_vcpus) \
        .withMemorySize(master_memory) \
        .withDiskSize(master_storage) \
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


def create_sona_network(sona, network, subnet):
    r = sona.create_network(network)
    if r.status_code != 201:
        return False

    r = sona.create_subnet(subnet)
    if r.status_code != 201:
        sona.delete_network(network)
        return False

    return True


def remove_cluster(cid):
    try:
        logging.info("Delete cluster for " + cid)
        cluster = K8sCatalog.objects.get(cluster_id=cid)
    except K8sCatalog.DoesNotExist:
        logging.error("Not found!!")
        return HttpResponse(status=404)

    app = ApplicationCatalog.objects.filter(cluster_id=cid)
    if len(app) > 0:
        app.delete()

    delete_cluster(cid)

    # remove all ONOS data and edgetron network data
    r = remove_network_data(cid)
    if not r:
        return False

    cluster.delete()
    return True


def delete_cluster(cid):
    worker_set = cid + "-" + "worker-set"
    master_name = cid + "-" + "master"
    delete_machineset(worker_set)
    time.sleep(20)
    delete_machine(master_name)
    delete_cluster(cid)


def remove_network_data(cid):
    sona = SonaHandler(sona_ip)
    vnet = SonaNetwork.objects.get(cluster_id=cid)
    subnet = SonaSubnet.objects.get(network_id=vnet.network_id)
    ports = SonaPort.objects.filter(cluster_id=cid)

    for port in ports:
        logging.info("Trying to delete port " + str(port))
        r = sona.delete_port(port)
        if r.status_code != 204:
            logging.error("SONA port delete error")
            return False
        port.delete()

    r = sona.delete_subnet(subnet)
    if r.status_code != 204:
        logging.error("SONA subnet delete error")
        return False
    subnet.delete()

    r = sona.delete_network(vnet)
    if r.status_code != 204:
        logging.error("SONA network delete error")
        return False
    vnet.delete()

    return True

@csrf_exempt
def os_images(request):
    """
    List all VM OS images.
    """
    if request.method == 'GET':
        response = {"image_names": os_image_list}
        return JsonResponse(response, safe=False)

@csrf_exempt
def kubernetes_versions(request):
    """
    List all kubernetes versions.
    """
    if request.method == 'GET':
        response = {"kubernetes_versions": k8s_ver_list}
        return JsonResponse(response, safe=False)


def wait_until_vm_is_created(cluster_id):
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


def create_sona_ports(sona, subnet, cluster_id):
    cluster_status = get_cluster_status(cluster_id)
    for machine, status in cluster_status.items():
        vm_status = status['vm']
        networks = vm_status['networks']

        for network in networks:
            mac = network['macAddress']
            ip = network['ipAddress']
            intf = network['interfaceName']
            name = network['networkName']
            port_id = intf[3:]

            if name == flat_network_id:
                sona_network_id = flat_network_id
                sona_subnet_id = flat_subnet_id
            else:
                sona_network_id = subnet.network_id
                sona_subnet_id = subnet.network_id

            port = SonaPort(port_id=port_id,
                            cluster_id=cluster_id,
                            subnet_id=sona_subnet_id,
                            network_id=sona_network_id,
                            tenant_id=subnet.tenant_id,
                            ip_address=ip,
                            mac_address=mac)
            port.save()

            r = sona.create_port(port)
            if r.status_code != 201:
                port.delete()
                logging.error("SONA create port error!")
                return False

    return True


def get_cluster_info():
    clusters = K8sCatalog.objects.all()
    cluster_info = []
    for cluster in clusters:
        dashboard_url = get_dashboard_url(cluster.interfaces.ip_address)
        cluster_item = {"cluster_id": cluster.cluster_id, "cluster_name": cluster.name, "dashboard_url": dashboard_url}
        cluster_info.append(json.dumps(cluster_item))

    response = {"cluster_info": cluster_info}

    return JsonResponse(response, safe=False)


def get_dashboard_url(ip_address):
    if ip_address != "":
        dashboard_url = "http://" + ip_address + ":9090"
    else:
        dashboard_url = ""
    return dashboard_url


def get_application_info():
    apps = ApplicationCatalog.objects.all()
    app_info = []
    for app in apps:
        app_item = {"cluster_id": app.cluster_id, "application_name": app.application_name}
        app_info.append(json.dumps(app_item))
    app_info_response = {"applicaiton_info: ": app_info}

    return JsonResponse(app_info_response, safe=False)


def get_application_detail(cid, app_name):
    app_list = get_app_list(cid)
    chart_status_list = []
    for name, status in app_list.items():
        resource_name = status['resource_name']
        resource_type = status['resource_type']
        app_version = status['app_version']
        helm_chart = status['helm_chart']
        release_name = status['release_name']
        replicas = str(status['replicas'])
        ready_replicas = str(status['ready_replicas'])
        ready = ready_replicas + "/" + replicas

        if ready_replicas == replicas:
            chart_status = "Deployed"
        else:
            chart_status = "Deploying"
        chart_status = {"release_name": release_name,
                        "status": chart_status,
                        "chart": helm_chart}
        chart_status_list.append(json.dumps(chart_status))

    app_detail_response = {"cluster_id": cid,
                           "application_name": app_name,
                           "chart_status": chart_status_list}

    return app_detail_response


def get_helm_status(cluster_status):
    master_vm_ip = get_master_ip(cluster_status)
    logging.info("master node VM IP is " + master_vm_ip)
    if master_vm_ip == "0.0.0.0":
        return "Not Ready"
    command = "helm list"
    key_file = "id_rsa_k8s"
    no_prompt = "-o StrictHostKeyChecking no"
    host_access = "kubernetes@" + master_vm_ip

    try:
        ssh_output = subprocess.check_output(["ssh", "-i", key_file, no_prompt, host_access, command],
                                             stdin=None, stderr=None, universal_newlines=False, shell=False)
    except subprocess.CalledProcessError:
        return "Not Ready"

    logging.info(ssh_output)

    return "Ready"


def set_repository(cid, repo):
    cluster_status = get_cluster_status(cid)
    master_vm_ip = get_master_ip(cluster_status)
    command_to_add_repo = "helm repo add " + repo.name + " " + repo.url
    key_file = "id_rsa_k8s"
    no_prompt = "-o StrictHostKeyChecking no"
    host_access = "kubernetes@" + master_vm_ip

    logging.info(command_to_add_repo)
    ssh_output = subprocess.check_output(["ssh", "-i", key_file, no_prompt, host_access, command_to_add_repo],
                                         stdin=None, stderr=None, universal_newlines=False, shell=False)
    logging.info(ssh_output)


def deploy_chart(cid, app_name, chart, mode):
    cluster_status = get_cluster_status(cid)
    master_vm_ip = get_master_ip(cluster_status)
    if mode == "install":
        command = "helm " + mode + " " + app_name + " " + chart.name
    else:
        command = "helm " + mode + " " + app_name
    key_file = "id_rsa_k8s"
    no_prompt = "-o StrictHostKeyChecking no"
    host_access = "kubernetes@" + master_vm_ip

    logging.info(command)
    try:
        ssh_output = subprocess.check_output(["ssh", "-i", key_file, no_prompt, host_access, command],
                                             stdin=None, stderr=None, shell=False, universal_newlines=False)
    except subprocess.CalledProcessError:
        return False

    logging.info(ssh_output)
    return True


def get_master_ip(cluster_status):
    master_ip = "0.0.0.0"
    logging.info("get_master_info")
    logging.info(cluster_status)
    for machine, status in cluster_status.items():
        machine_name = machine
        logging.info(machine_name)
        if machine_name[-6:] == "master":
            vm_status = status['vm']
            vm_state = vm_status['state']
            logging.info(vm_status)
            if vm_state == "Running":
                networks = vm_status['networks']
                logging.info(networks)
                flat_network = networks[0]
                master_ip = flat_network['ipAddress']

    return master_ip


def create_flat_network(sona):
    flat_network = SonaNetwork(cluster_id="FLAT_K8S_NET_ID",
                               network_id=flat_network_id,
                               name="k8s_flat_network",
                               segment_id=0,
                               tenant_id=0)
    r = sona.create_network(flat_network)
    if r.status_code != 201:
        logging.error("Flat network creation error in SONA")
        return False

    flat_subnet = SonaSubnet(network_id=flat_network_id,
                             subnet_id=flat_subnet_id,
                             tenant_id=0,
                             name="k8s flat subnet",
                             cidr=flat_network_cidr)
    r = sona.create_subnet(flat_subnet)
    if r.status_code != 201:
        logging.error("Flat sub-network creation error in SONA")
        return False

    return True
