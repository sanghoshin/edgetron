from django.urls import include, path
from edgetron import views
# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('edgetron/resources/kubernetes', views.kubernetes_cluster),
    path('edgetron/resources/kubernetes/clear', views.clean_up_all),
    path('edgetron/resources/kubernetes/image', views.os_images),
    path('edgetron/resources/kubernetes/version', views.kubernetes_versions),
    path('edgetron/resources/kubernetes/<cid>', views.kubernetes_cluster_info),
    path('edgetron/resources/kubernetes/application/deployment', views.deployment),
    path('edgetron/resources/kubernetes/application/deployment/<cid>', views.application_detail)
]
