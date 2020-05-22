from rest_framework import serializers
from edgetron.models import K8sCatalog, Scaling, Interface

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

    class Meta:
        model = K8sCatalog
        fields = ['scaling', 'interfaces', 'masterNodes', 'memory', 'storage', 'vcpus']

    def create(self, validated_data):
        scaling_data = validated_data.pop('scaling')
        scaling = Scaling.objects.create(**scaling_data)

        interface_data = validated_data.pop('interfaces')
        interfaces = Interface.objects.create(**interface_data)

        masterNodes = validated_data.pop('masterNodes')
        memory = validated_data.pop('memory')
        storage = validated_data.pop('storage')
        vcpus = validated_data.pop('vcpus')

        k8s_data = K8sCatalog.objects.create(scaling=scaling, interfaces=interfaces, clusterId=str(uuid.uuid4()),
                                           masterNodes=masterNodes, memory=memory, storage=storage,
                                             vcpus=vcpus)

        return k8s_data

