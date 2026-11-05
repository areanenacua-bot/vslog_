from django.db import models
from django.core.exceptions import ValidationError

class Office(models.Model):
    office_id = models.AutoField(primary_key=True)
    office_name = models.CharField(max_length=150, unique=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.office_name


class Visitor(models.Model):
    VISITOR_TYPES = [
        ('Parent/Guardian', 'Parent/Guardian'),
        ('Alumni', 'Alumni'),
        ('Delivery Personnel', 'Delivery Personnel'),
        ('Contractor', 'Contractor'),
        ('Government Personnel', 'Government Personnel'),
        ('Guest', 'Guest'),
        ('Other', 'Other'),
    ]

    visitor_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    address = models.TextField(blank=True, null=True)
    visitor_type = models.CharField(max_length=50, choices=VISITOR_TYPES)
    visitor_type_other = models.CharField('Other visitor type', max_length=100, blank=True, default='')

    def clean(self):
        super().clean()
        self.visitor_type_other = self.visitor_type_other.strip()
        if self.visitor_type == 'Other' and not self.visitor_type_other:
            raise ValidationError({'visitor_type_other': 'Please specify the visitor type.'})
        if self.visitor_type != 'Other':
            self.visitor_type_other = ''

    @property
    def visitor_type_display(self):
        if self.visitor_type == 'Other' and self.visitor_type_other:
            return f'Other: {self.visitor_type_other}'
        return self.get_visitor_type_display()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.visitor_type_display})"


class Visit(models.Model):
    STATUS_CHOICES = [
        ('Inside', 'Inside'),
        ('Completed', 'Completed'),
    ]

    visit_id = models.AutoField(primary_key=True)
    visitor = models.ForeignKey(Visitor, on_delete=models.PROTECT, related_name='visits')
    office = models.ForeignKey(Office, on_delete=models.PROTECT, related_name='visits')
    recorded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    purpose = models.TextField()
    person_to_visit = models.CharField(max_length=150, blank=True, null=True)
    time_in = models.DateTimeField(auto_now_add=True)
    time_out = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Inside')

    def __str__(self):
        return f"Visit: {self.visitor} -> {self.office} [{self.status}]"
