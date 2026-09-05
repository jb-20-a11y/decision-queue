from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Item, StatusChoices
from .serializers import ItemCreateSerializer, ItemSerializer, ItemUpdateSerializer


class ItemViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.items_url = "/api/items/"

    def item_payload(self, title="Improve onboarding", urgency=4):
        return {
            "title": title,
            "problem_statement": "New users are unsure what to do first.",
            "urgency": urgency,
            "expected_impact": 5,
        }

    def test_create_item(self):
        response = self.client.post(self.items_url, self.item_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Item.objects.count(), 1)
        item = Item.objects.get()
        self.assertEqual(item.title, "Improve onboarding")
        self.assertEqual(item.urgency, 4)
        self.assertEqual(item.expected_impact, 5)
        self.assertEqual(item.status, StatusChoices.PENDING)
        self.assertEqual(response.data["title"], item.title)
        self.assertEqual(response.data["problem_statement"], item.problem_statement)
        self.assertEqual(response.data["urgency"], item.urgency)
        self.assertEqual(response.data["expected_impact"], item.expected_impact)

    def test_update_item(self):
        item = Item.objects.create(
            **self.item_payload(),
            status=StatusChoices.PENDING,
            status_reason="Awaiting review.",
        )

        response = self.client.post(
            f"{self.items_url}{item.pk}/",
            {"status": StatusChoices.ACCEPTED, "status_reason": "Approved."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.status, StatusChoices.ACCEPTED)
        self.assertEqual(item.status_reason, "Approved.")
        self.assertEqual(response.data["status"], StatusChoices.ACCEPTED)
        self.assertEqual(response.data["status_reason"], "Approved.")

    def test_list_orders_items_by_primary_key_by_default(self):
        created_items = [
            Item.objects.create(
                **self.item_payload(title=title, urgency=urgency),
                status=StatusChoices.PENDING,
                status_reason="Awaiting review.",
            )
            for title, urgency in (("First", 5), ("Second", 1), ("Third", 3))
        ]

        response = self.client.get(self.items_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["title"] for item in response.data["results"]],
            [item.title for item in created_items],
        )

    def test_list_orders_items_by_urgency_descending(self):
        for title, urgency in (("Low", 1), ("Highest", 5), ("Medium", 3)):
            Item.objects.create(
                **self.item_payload(title=title, urgency=urgency),
                status=StatusChoices.PENDING,
                status_reason="Awaiting review.",
            )

        response = self.client.get(self.items_url, {"ordering": "urgency"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["title"] for item in response.data["results"]],
            ["Highest", "Medium", "Low"],
        )

    def test_list_filters_items_by_status(self):
        Item.objects.create(
            **self.item_payload(title="Pending item"),
            status=StatusChoices.PENDING,
            status_reason="Awaiting review.",
        )
        Item.objects.create(
            **self.item_payload(title="Accepted item"),
            status=StatusChoices.ACCEPTED,
            status_reason="Approved.",
        )

        response = self.client.get(self.items_url, {"status": "accepted"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Accepted item")

    def test_list_rejects_invalid_status_filter(self):
        response = self.client.get(self.items_url, {"status": "unknown"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["status"], "Invalid status.")

    def test_list_is_paginated(self):
        for index in range(51):
            Item.objects.create(
                **self.item_payload(title=f"Item {index}"),
                status=StatusChoices.PENDING,
                status_reason="Awaiting review.",
            )

        first_page = self.client.get(self.items_url)
        second_page = self.client.get(self.items_url, {"page": 2})

        self.assertEqual(first_page.status_code, status.HTTP_200_OK)
        self.assertEqual(first_page.data["count"], 51)
        self.assertEqual(len(first_page.data["results"]), 50)
        self.assertIsNotNone(first_page.data["next"])
        self.assertIsNone(first_page.data["previous"])
        self.assertEqual(second_page.status_code, status.HTTP_200_OK)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertEqual(second_page.data["results"][0]["title"], "Item 50")


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
