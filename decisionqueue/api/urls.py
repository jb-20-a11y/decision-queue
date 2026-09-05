from django.urls import path
from django.urls import path

from .views import ItemListCreateView, ItemUpdateView

urlpatterns = [
    path("items/", ItemListCreateView.as_view(), name="item-list-create"),
    path("items/<int:pk>/", ItemUpdateView.as_view(), name="item-update"),
]
