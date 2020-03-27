from rest_framework import serializers
from edgetron.models import Catalog


class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        mode = Catalog
        fields = [id, name, desc]

