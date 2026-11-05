---
name: school-visitor-log-system
description: Complete Django 6.1, Bootstrap 5, and MySQL development guide, data models, UI palette, and role matrix for the MinSU-SND Web-Based School Visitor Log Management System.
---

# School Visitor Log Management System (MinSU-SND)

Use this skill for any work on the Technical Elective 4 project: the Web-Based School Visitor Log Management System for Mindanao State University - Sultan Naga Dimaporo. It covers backend structure, data model, screens, and the visual design. Always follow the project documentation (Deliverable 1) below. Do not invent features outside its scope.

## 1. Fixed Project Facts
- **Stack (do not substitute):** Python 3.13, Django 6.1.x, HTML5, CSS3, Bootstrap 5, MySQL (SQLite allowed only for local dev), Git/GitHub, VS Code.
- **Purpose:** Digitize recording and monitoring of non-student school visitors (parents/guardians, alumni, delivery, contractors, government personnel, guests). Replaces paper logbook.
- **Roles:**
  - `Administrator`: Everything staff can do, plus manage user accounts, manage offices/destinations, view basic reports/dashboard for all records.
  - `Security Personnel / Authorized Staff`: Log in/out, register visitor, record visit and time-in, record time-out, view active visitors, search/view history.
  - `Visitor`: External actor (provides info only; never logs in).
- **Out of scope (never add):** Student/employee attendance, enrollment, grading, physical access control, biometrics, face recognition, RFID/NFC, automated ID verification, background checks, visitor self-service accounts.

---

## 2. Data Model (Match ERD Exactly)

```python
# users: extend AbstractUser; AUTH_USER_MODEL = 'accounts.User'
class User(AbstractUser):
    ROLE = [('ADMIN', 'Administrator'), ('STAFF', 'Staff')]
    role = models.CharField(max_length=30, choices=ROLE, default='STAFF')

class Visitor(models.Model):
    TYPES = [('PARENT','Parent/Guardian'),('ALUMNI','Alumni'),('DELIVERY','Delivery'),
             ('CONTRACTOR','Contractor'),('GOVT','Government Personnel'),
             ('GUEST','Guest'),('OTHER','Other')]
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    visitor_type = models.CharField(max_length=50, choices=TYPES)

class Office(models.Model):
    office_name = models.CharField(max_length=100)
    location = models.CharField(max_length=150, blank=True)

class Visit(models.Model):
    STATUS = [('INSIDE','Inside'),('COMPLETED','Completed')]
    visitor = models.ForeignKey(Visitor, on_delete=models.PROTECT, related_name='visits')
    office = models.ForeignKey(Office, on_delete=models.PROTECT, related_name='visits')
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    purpose = models.CharField(max_length=255)
    person_to_visit = models.CharField(max_length=150, blank=True, null=True)
    time_in = models.DateTimeField(default=timezone.now)
    time_out = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default='INSIDE')


:root {
  --minsu-maroon:      #6D1926; /* Primary: sidebar accents, buttons, headings */
  --minsu-maroon-700:  #55121C; /* Hover/pressed */
  --minsu-maroon-50:   #F7E9EB; /* Tinted backgrounds */
  --minsu-gold:        #E2C756; /* Accent: highlights, active nav, CTA ring */
  --minsu-gold-600:    #C9A63A; /* Gold text on light backgrounds */
  --minsu-gold-100:    #FBF3D3; /* Greeting banner background */
  --minsu-green:       #2D6E12; /* Success: Completed status */
  --minsu-green-500:   #5F860F; /* Sprout green */
  --minsu-green-50:    #EAF3DF;
  --minsu-ink:         #2B1E20; /* Body text */
  --minsu-muted:       #7A6E70;
  --minsu-bg:          #FBF7EC; /* Canvas background (warm cream) */
  --minsu-surface:     #FFFFFF;
  --minsu-line:        #EADFD0;
}



URL PathScreen NameAccess Level/login/, /logout/Auth PortalPublic / Authenticated/Main DashboardAuthenticated/visits/register/Register Visitor + Time-InAuthenticated/visits/active/Active Visitors (Time Out)Authenticated/visits/history/Visitor History + FiltersAuthenticated/visits/<id>/timeout/Record Time-Out (POST)Authenticated/visitors/Visitor Directory & EditAuthenticated/offices/Office ManagementAdmin Only/users/Account ManagementAdmin Only

