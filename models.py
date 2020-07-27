from django.db import models


class Scaling(models.Model):
    current = models.IntegerField()
    maximum = models.IntegerField()
    minimum = models.IntegerField()


class Interface(models.Model):
    ip_version = models.IntegerField(default=4)
    ip_address = models.CharField(max_length=19, blank=False)

    def __str__(self):
        return "(" + self.ip_address + ")"


class K8sCatalog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=40, blank=True)
    scaling = models.ForeignKey(Scaling, related_name="catalog",
                                on_delete=models.CASCADE)
    interfaces = models.ForeignKey(Interface, related_name="catalog",
                                   on_delete=models.CASCADE)
    cluster_id = models.CharField(max_length=40, blank=False, primary_key=True)
    master_nodes = models.IntegerField()
    memory = models.IntegerField()
    storage = models.IntegerField()
    vcpus = models.IntegerField()
    version = models.CharField(max_length=10, blank=True, default="1.17")
    image = models.CharField(max_length=20, blank=False, default="ubuntu")

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.cluster_id + ":" + str(self.interfaces) + " : " + str(self.memory)


class Repository(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=40, blank=True)
    url = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name + " : " + self.url


class Chart(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    order = models.IntegerField()
    chart_id = models.CharField(max_length=40, blank=True, default="0")
    name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.chart_id + " : " + self.name


class ApplicationCatalog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    application_name = models.CharField(max_length=40, blank=False)
    cluster_id = models.CharField(max_length=40, blank=False, primary_key=True)
    repositories = models.ManyToManyField(Repository)
    charts = models.ManyToManyField(Chart)

    def __str__(self):
        return self.cluster_id + " : " + self.application_name


class SonaNetwork(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    cluster_id = models.CharField(max_length=40, blank=False, primary_key=True)
    network_id = models.CharField(max_length=40, blank=False)
    segment_id = models.CharField(max_length=40, blank=False)
    tenant_id = models.CharField(max_length=40, blank=False)
    name = models.CharField(max_length=100, blank=False)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.cluster_id + " : " + self.network_id + " : " + self.segment_id + " : " + self.tenant_id


class SonaSubnet(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    subnet_id = models.CharField(max_length=40, blank=False)
    network_id = models.CharField(max_length=40, blank=False)
    tenant_id = models.CharField(max_length=40, blank=False)
    cidr = models.CharField(max_length=22, blank=False)
    name = models.CharField(max_length=100, blank=False)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.network_id + " : " + self.subnet_id + " : " + self.cidr


class SonaPort(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    cluster_id = models.CharField(max_length=40, blank=False)
    port_id = models.CharField(max_length=40, blank=False, primary_key=True)
    subnet_id = models.CharField(max_length=40, blank=False)
    network_id = models.CharField(max_length=40, blank=False)
    tenant_id = models.CharField(max_length=40, blank=False)
    ip_address = models.CharField(max_length=15, blank=False, default="127.0.0.1")
    mac_address = models.CharField(max_length=25, blank=False)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.network_id + " : " + self.subnet_id + " : " + \
               self.port_id + " : " + self.ip_address + " : " + self.mac_address
