from rest_framework import generics, serializers
from rest_framework.pagination import PageNumberPagination

from .models import Item, StatusChoices
from .serializers import ItemCreateSerializer, ItemListSerializer, ItemUpdateSerializer


class ItemPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = None


class ItemListCreateView(generics.ListCreateAPIView):
    pagination_class = ItemPagination

    def get_queryset(self):
        queryset = Item.objects.all()
        status = self.request.query_params.get("status", "all")
        if status.lower() != "all":
            status_values = {label.lower(): value for value, label in StatusChoices.choices}
            try:
                status_value = status_values[status.lower()]
            except KeyError:
                raise serializers.ValidationError({"status": "Invalid status."})
            queryset = queryset.filter(status=status_value)

        if self.request.query_params.get("ordering", "id").lower() == "urgency":
            return queryset.order_by("-urgency")
        return queryset.order_by("id")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ItemCreateSerializer
        return ItemListSerializer


class ItemUpdateView(generics.UpdateAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemUpdateSerializer
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
