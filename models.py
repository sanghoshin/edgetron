from django.db import models


class Scaling(models.Model):
    init = models.IntegerField()
    maximum = models.IntegerField()
    minimum = models.IntegerField()


class Interface(models.Model):
    ipVersion = models.CharField(max_length=4, blank=False, default='IPv4')
    ipAddress = models.CharField(max_length=19, blank=False)


class K8sCatalog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    scaling = models.ForeignKey(Scaling, related_name="catalog",
                                on_delete=models.CASCADE)
    interfaces = models.ForeignKey(Interface, related_name="catalog",
                                   on_delete=models.CASCADE)
    masterNodes = models.IntegerField()
    memory = models.IntegerField()
    storage = models.IntegerField()
    vcpus = models.IntegerField()

    class Meta:
        ordering = ['created']


class Network(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    networkId = models.CharField(max_length=40, blank=False)
    segmentId = models.CharField(max_length=40, blank=False)
    tenantId = models.CharField(max_length=40, blank=False)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.networkId + " : " + self.segmentId + " : " + self.tenantId


class Subnet(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    subnetId = models.CharField(max_length=40, blank=False)
    networkId = models.CharField(max_length=40, blank=False)
    tenantId = models.CharField(max_length=40, blank=False)
    cidr = models.CharField(max_length=22, blank=False)
    startIp = models.CharField(max_length=19, blank=False)
    endIp = models.CharField(max_length=19, blank=False)
    gateway = models.CharField(max_length=19, blank=False)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.networkId + " : " + self.subnetId + " : " + self.cidr


class Port(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    portId = models.CharField(max_length=40, blank=False)
    subnetId = models.CharField(max_length=40, blank=False)
    networkId = models.CharField(max_length=40, blank=False)
    tenantId = models.CharField(max_length=40, blank=False)
    ipAddress = models.CharField(max_length=15, blank=False)
    macAddress = models.CharField(max_length=25, blank=False)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.networkId + " : " + self.subnetId + " : " + \
               self.portId + " : " + self.ipAddress + " : " + self.macAddress