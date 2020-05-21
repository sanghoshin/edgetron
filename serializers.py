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
        #validated_data['k8s_cluster_id'] = str(uuid.uuid4())
        scaling_data = validated_data.pop('scaling')

        #clusterId = uuid.uuid4()
        k8s_data = K8sCatalog.objects.create(**validated_data)

        scaling = Scaling.objects.create(scaling_data)
        k8s_data['scaling'] = scaling

        #k8s_data['k8s_cluster_id'] = str(uuid.uuid4())
        return k8s_data

