from django.db import models

class UrgencyChoices(models.IntegerChoices):
    LOWEST = 1, "Lowest"
    LOW = 2, "Low"
    MEDIUM = 3, "Medium"
    HIGH = 4, "High"
    HIGHEST = 5, "Highest"

class ExpectedImpactChoices(models.IntegerChoices):
    LOWEST = 1, "Lowest"
    LOW = 2, "Low"
    MEDIUM = 3, "Medium"
    HIGH = 4, "High"
    HIGHEST = 5, "Highest"


class StatusChoices(models.IntegerChoices):
    PENDING = 1, "Pending"
    DEFERRED = 2, "Deferred"
    ACCEPTED = 3, "Accepted"
    DECLINED = 4, "Declined"

class Item(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=100)
    problem_statement = models.TextField()
    urgency = models.IntegerField(choices=UrgencyChoices.choices)
    expected_impact = models.IntegerField(choices=ExpectedImpactChoices.choices)
    status = models.IntegerField(choices=StatusChoices.choices)
    status_reason = models.TextField()

    class Meta:
        indexes = [models.Index(fields=["-urgency"])]



