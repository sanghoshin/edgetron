from django.db import models


class Scaling(models.Model):
    init = models.IntegerField()
    maximum = models.IntegerField()
    minimum = models.IntegerField()


class Interface(models.Model):
    ip_version = models.CharField(max_length=4, blank=False, default='IPv4')
    ip_address = models.CharField(max_length=19, blank=False)


class K8sCatalog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    scaling = models.ForeignKey(Scaling, related_name="catalog",
                                on_delete=models.CASCADE)
    interfaces = models.ForeignKey(Interface, related_name="catalog",
                                   on_delete=models.CASCADE)
    master_nodes = models.IntegerField()
    memory = models.IntegerField()
    storage = models.IntegerField()
    vcpus = models.IntegerField()

    class Meta:
        ordering = ['created']
