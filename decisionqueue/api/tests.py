from django.test import TestCase

from .models import Item, StatusChoices
from .serializers import ItemCreateSerializer, ItemSerializer, ItemUpdateSerializer


class ItemSerializerTests(TestCase):
    def setUp(self):
        self.item_attributes = {
            "title": "Improve onboarding",
            "problem_statement": "New users are unsure what to do first.",
            "urgency": 4,
            "expected_impact": 5,
            "status": 1,
            "status_reason": "Awaiting review.",
        }
        self.serializer_data = {
            "title": "Improve onboarding",
            "problem_statement": "New users are unsure what to do first.",
            "urgency": "Highest",
            "expected_impact": "Low",
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
                "expected_impact",
                "status",
                "status_reason",
            },
        )

    def test_serializes_choice_integers_as_text(self):
        data = self.serializer.data

        self.assertEqual(data["urgency"], "High")
        self.assertEqual(data["expected_impact"], "Highest")
        self.assertEqual(data["status"], "Pending")

    def test_deserializes_choice_text_as_integers(self):
        serializer = ItemSerializer(data=self.serializer_data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["urgency"], 5)
        self.assertEqual(serializer.validated_data["expected_impact"], 2)
        self.assertEqual(serializer.validated_data["status"], 3)

    def test_rejects_invalid_choice_text(self):
        invalid_data = {
            **self.serializer_data,
            "urgency": "Urgent",
            "expected_impact": "Critical",
            "status": "In progress",
        }
        serializer = ItemSerializer(data=invalid_data)

        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            set(serializer.errors), {"urgency", "expected_impact", "status"}
        )


class ItemCreateSerializerTests(TestCase):
    def test_create_sets_status_to_pending(self):
        serializer = ItemCreateSerializer(
            data={
                "title": "Improve onboarding",
                "problem_statement": "New users are unsure what to do first.",
                "urgency": 4,
                "expected_impact": 5,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        item = serializer.save()

        self.assertEqual(item.status, StatusChoices.PENDING)


class ItemUpdateSerializerTests(TestCase):
    def test_update_changes_date_modified(self):
        item = Item.objects.create(
            title="Improve onboarding",
            problem_statement="New users are unsure what to do first.",
            urgency=4,
            expected_impact=5,
            status=StatusChoices.PENDING,
            status_reason="Awaiting review.",
        )
        original_modified = item.date_modified
        serializer = ItemUpdateSerializer(
            instance=item,
            data={
                "status": 3,
                "status_reason": "The team approved the change.",
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_item = serializer.save()
        updated_item.refresh_from_db()

        self.assertEqual(updated_item.status, StatusChoices.ACCEPTED)
        self.assertEqual(updated_item.status_reason, "The team approved the change.")
        self.assertGreater(updated_item.date_modified, original_modified)
