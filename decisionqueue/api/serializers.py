from rest_framework import serializers
from .models import Item

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

