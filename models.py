from django.db import models


class Scaling(models.Model):
    init = models.IntegerField()
    maximum = models.IntegerField()
    minimum = models.IntegerField()


class Interface(models.Model):
    ipVersion = models.CharField(max_length=4, blank=False, default='IPv4')
    ipAddress = models.CharField(max_length=19, blank=False)

    def __str__(self):
        return "(" + self.ipAddress + ")"


class K8sCatalog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=40, blank=True)
    scaling = models.ForeignKey(Scaling, related_name="catalog",
                                on_delete=models.CASCADE)
    interfaces = models.ForeignKey(Interface, related_name="catalog",
                                   on_delete=models.CASCADE)
    clusterId = models.CharField(max_length=40, blank=False, default="0")
    masterNodes = models.IntegerField()
    memory = models.IntegerField()
    storage = models.IntegerField()
    vcpus = models.IntegerField()
    version = models.CharField(max_length=10, blank=True, default="1.17")
    image = models.CharField(max_length=20, blank=False, default="ubuntu")

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.clusterId + ":" + str(self.interfaces) + " : " + str(self.memory)


class SonaNetwork(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    clusterId = models.CharField(max_length=40, blank=False, default="0")
    networkId = models.CharField(max_length=40, blank=False)
    segmentId = models.CharField(max_length=40, blank=False)
    tenantId = models.CharField(max_length=40, blank=False)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.clusterId + " : " + self.networkId + " : " + self.segmentId + " : " + self.tenantId


class SonaSubnet(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    subnetId = models.CharField(max_length=40, blank=False)
    networkId = models.CharField(max_length=40, blank=False)
    tenantId = models.CharField(max_length=40, blank=False)
    cidr = models.CharField(max_length=22, blank=False)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.networkId + " : " + self.subnetId + " : " + self.cidr


class SonaPort(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    portId = models.CharField(max_length=40, blank=False)
    subnetId = models.CharField(max_length=40, blank=False)
    networkId = models.CharField(max_length=40, blank=False)
    tenantId = models.CharField(max_length=40, blank=False)
    ipAddress = models.CharField(max_length=15, blank=False, default="127.0.0.1")
    macAddress = models.CharField(max_length=25, blank=False)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.networkId + " : " + self.subnetId + " : " + \
               self.portId + " : " + self.ipAddress + " : " + self.macAddress