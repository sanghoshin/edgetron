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
        fields = ['ipVersion', 'ipAddress']


class K8sCatalogSerializer(serializers.ModelSerializer):
    scaling = ScalingSerializer()
    interfaces = InterfaceSerializer()
    clusterId = str(uuid.uuid4())
    clusterName = ""
    vcpus = ""
    memory = ""
    storage = ""
    version = ""
    image = ""
    masterNodes = 0

    class Meta:
        model = K8sCatalog
        fields = ['name', 'scaling', 'interfaces', 'masterNodes', 'memory', 'storage', 'vcpus', 'image', 'version']

    def create(self, validated_data):
        scaling_data = validated_data.pop('scaling')
        self.scaling = Scaling.objects.create(**scaling_data)

        interface_data = validated_data.pop('interfaces')
        self.interfaces = Interface.objects.create(**interface_data)

        self.clusterName = validated_data.pop('name')
        self.masterNodes = validated_data.pop('masterNodes')
        self.memory = validated_data.pop('memory')
        self.storage = validated_data.pop('storage')
        self.vcpus = validated_data.pop('vcpus')
        self.version = validated_data.pop('version')
        self.image = validated_data.pop('image')

        k8s_data = K8sCatalog.objects.create(name=self.clusterName, scaling=self.scaling, interfaces=self.interfaces,
                                             clusterId=self.clusterId, masterNodes=self.masterNodes, memory=self.memory,
                                             storage=self.storage, vcpus=self.vcpus, version=self.version, image=self.image)

        return k8s_data


class AppCatalogSerializer(serializers.ModelSerializer):
    applicationId = ""
    clusterId = ""
    repository = RepositorySerializer()
    chart = ChartSerializer()

    class Meta:
        model = ApplicationCatalog
        fields = ['application ID', 'cluster ID', 'repository', 'chart']

    def create(self, validated_data):
        self.applicationId = validated_data.pop('application ID')
        self.clusterId = validated_data.pop('cluster ID')
        repository_data = validated_data.pop('repository')
        self.repository = Repository.objects.create(**repository_data)
        chart_data = validated_data.pop('chart')
        self.repository = Chart.objects.create(**chart_data)

        appData = ApplicationCatalog.objects.create(clusterId=self.clusterId,
                                                    applicationId=self.applicationId,
                                                    repository=self.repository,
                                                    chart=self.chart)
        return appData

class RepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = ['name', 'url']

class ChartSerialization(serializers.ModelSerializer):
    class Meta:
        model = Chart
        fields = ['id', 'name']
