from django.urls import include, path
from edgetron import views
# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('edgetron/catalog/', views.catalog_list),
    path('edgetron/catalog/<int:pk>/action/onboard', views.catalog_onboard),
]
