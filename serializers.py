from rest_framework import serializers
from edgetron.models import K8sCatalog, Scaling, Interface, ApplicationCatalog, Repository, Chart

import uuid


class ScalingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scaling
        fields = ['init', 'maximum', 'minimum']


class InterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interface
        fields = ['ip_version', 'ip_address']


class K8sCatalogSerializer(serializers.ModelSerializer):
    scaling = ScalingSerializer()
    interfaces = InterfaceSerializer()
    cluster_id = str(uuid.uuid4())
    cluster_name = ""
    vcpus = ""
    memory = ""
    storage = ""
    version = ""
    image = ""
    master_nodes = 0

    class Meta:
        model = K8sCatalog
        fields = ['name', 'scaling', 'interfaces', 'master_nodes', 'memory', 'storage', 'vcpus', 'image', 'version']

    def create(self, validated_data):
        scaling_data = validated_data.pop('scaling')
        self.scaling = Scaling.objects.create(**scaling_data)

        interface_data = validated_data.pop('interfaces')
        self.interfaces = Interface.objects.create(**interface_data)

        self.cluster_name = validated_data.pop('name')
        self.master_nodes = validated_data.pop('master_nodes')
        self.memory = validated_data.pop('memory')
        self.storage = validated_data.pop('storage')
        self.vcpus = validated_data.pop('vcpus')
        self.version = validated_data.pop('version')
        self.image = validated_data.pop('image')

        k8s_data = K8sCatalog.objects.create(name=self.cluster_name, scaling=self.scaling, interfaces=self.interfaces,
                                             cluster_id=self.cluster_id, master_nodes=self.master_nodes, memory=self.memory,
                                             storage=self.storage, vcpus=self.vcpus, version=self.version, image=self.image)

        return k8s_data


class RepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = ['name', 'url']


class ChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chart
        fields = ['chart_id', 'name']


class AppCatalogSerializer(serializers.ModelSerializer):
    application_name = ""
    cluster_id = ""
    repository = RepositorySerializer()
    chart = ChartSerializer()

    class Meta:
        model = ApplicationCatalog
        fields = ['application_name', 'cluster_id', 'repository', 'chart']

    def create(self, validated_data):
        self.application_name = validated_data.pop('application_name')
        self.cluster_id = validated_data.pop('cluster_id')
        repository_data = validated_data.pop('repository')
        self.repository = Repository.objects.create(**repository_data)
        chart_data = validated_data.pop('chart')
        self.chart = Chart.objects.create(**chart_data)

        appData = ApplicationCatalog.objects.create(cluster_id=self.cluster_id,
                                                    application_name=self.application_name,
                                                    repository=self.repository,
                                                    chart=self.chart)
        return appData
