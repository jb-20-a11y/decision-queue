from django.test import TestCase

from .models import Item
from .serializers import ItemSerializer


class ItemSerializerTests(TestCase):
    def setUp(self):
        self.item_attributes = {
            "title": "Improve onboarding",
            "problem_statement": "New users are unsure what to do first.",
            "urgency": 4,
            "status": 1,
            "status_reason": "Awaiting review.",
        }
        self.serializer_data = {
            "title": "Improve onboarding",
            "problem_statement": "New users are unsure what to do first.",
            "urgency": "Highest",
            "status": "Accepted",
            "status_reason": "The team approved the change.",
        }
        self.item = Item.objects.create(**self.item_attributes)
        self.serializer = ItemSerializer(instance=self.item)

    def test_contains_expected_fields(self):
        data = self.serializer.data

        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "date_created",
                "date_modified",
                "title",
                "problem_statement",
                "urgency",
                "status",
                "status_reason",
            },
        )

    def test_serializes_choice_integers_as_text(self):
        data = self.serializer.data

        self.assertEqual(data["urgency"], "High")
        self.assertEqual(data["status"], "Pending")

    def test_deserializes_choice_text_as_integers(self):
        serializer = ItemSerializer(data=self.serializer_data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["urgency"], 5)
        self.assertEqual(serializer.validated_data["status"], 3)
