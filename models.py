from django.db import models


class Catalog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=False, default='net')
    desc = models.TextField()

    class Meta:
        ordering = ['created']
