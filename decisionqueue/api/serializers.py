from rest_framework import serializers
from django.utils import timezone

from .models import Item, StatusChoices

class IntegerChoiceField(serializers.IntegerField):
    def __init__(self, choices, *args, **kwargs):
        self.choice_map = {label: val for val, label in choices}
        self.inverse_map = {val: label for val, label in choices}
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        # Convert integer from DB to choice text for reading
        return self.inverse_map.get(value, value)

    def to_internal_value(self, data):
        # Convert choice text from request to integer for writing
        if data in self.choice_map:
            return self.choice_map[data]
        raise serializers.ValidationError("Invalid choice.")

class ItemSerializer(serializers.ModelSerializer):
    urgency = IntegerChoiceField(choices=Item._meta.get_field('urgency').choices)
    status = IntegerChoiceField(choices=Item._meta.get_field('status').choices)
    expected_impact = IntegerChoiceField(choices=Item._meta.get_field('expected_impact').choices)
    class Meta:
        model = Item
        fields = '__all__'

class ItemListSerializer(serializers.ModelSerializer):
    urgency = IntegerChoiceField(choices=Item._meta.get_field('urgency').choices)
    status = IntegerChoiceField(choices=Item._meta.get_field('status').choices)
    expected_impact = IntegerChoiceField(choices=Item._meta.get_field('expected_impact').choices)

    class Meta:
        model = Item
        fields = (
            "title",
            "expected_impact",
            "urgency",
            "status",
            "date_created",
            "date_modified",
        )


class ItemCreateSerializer(serializers.ModelSerializer):
    urgency = IntegerChoiceField(choices=Item._meta.get_field('urgency').choices)
    expected_impact = IntegerChoiceField(choices=Item._meta.get_field('expected_impact').choices)

    class Meta:
        model = Item
        fields = ("title", "problem_statement", "urgency", "expected_impact")

    def create(self, validated_data):
        validated_data["status"] = StatusChoices.PENDING
        return super().create(validated_data)


class ItemUpdateSerializer(serializers.ModelSerializer):
    status = IntegerChoiceField(choices=Item._meta.get_field('status').choices)

    class Meta:
        model = Item
        fields = ("status", "status_reason")

    def update(self, instance, validated_data):
        instance.date_modified = timezone.now()
        return super().update(instance, validated_data)
