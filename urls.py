from django.urls import include, path
from edgetron import views
# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('edgetron/resources/kubernetes', views.kubernetes_cluster),
    path('edgetron/resources/kubernetes/{cid}', views.kubernetes_cluster_info),
    path('edgetron/resources/kubernetes/application/deployment/', views.deployment),
]
