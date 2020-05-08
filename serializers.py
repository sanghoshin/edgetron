from rest_framework import serializers
from edgetron.models import K8sCatalog, Scaling, Interface


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

