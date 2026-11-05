# School Visitor Log Management System

Django application implementing the workflow in `School_Visitor_Log_System_Whole_Concept.pdf`: locate or register a non-student visitor, record their purpose and destination, monitor their arrival, record departure, and retain searchable history.

## Run locally

Use Python 3.12 or newer. In PowerShell from this directory:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py createsuperuser
.\venv\Scripts\python.exe manage.py runserver
```

Open http://127.0.0.1:8000/. Existing installations can use their existing accounts. Administrators manage destinations at http://127.0.0.1:8000/admin/ under **Offices** before visitors are registered. Office names and locations are configured by the school rather than populated with fictional records.

## Accounts and responsibilities

Visitors do not have accounts. An administrator provisions accounts for authorized school personnel in Django Admin (**Users**).

The person in charge signs in at `/login/` with their assigned username and password. To provision that account, an administrator opens `/admin/`, adds a user, and leaves **Staff status** and **Superuser status** unchecked. Both personnel and administrators can use the visitor desk login; account permissions determine access. Administration links are omitted from the visitor desk sidebar for all accounts. Administrators access `/admin/` directly.

| Role | Django account configuration | Access |
| --- | --- | --- |
| Administrator | Active superuser (created using `createsuperuser`) | Daily workflow, user management and school office management |
| Security / authorized personnel | Active account, with **Staff status** and **Superuser status** unchecked | Dashboard, registration, active visitors, history and reports; no Django Admin access |

Django's **Staff status** flag controls access to the administrative site, not the security personnel role. Delegated administrators may instead have Staff status and explicitly assigned model permissions. Only grant account-management permissions to administrators trusted to manage authorization.

Accounts can be deactivated to prevent login while retaining the recorded-by attribution. Administrators use Django's password controls; passwords are hashed using Django authentication. Logout and changes to visit records require CSRF-protected POST requests.

## Daily workflow

1. Sign in with an authorized account.
2. Open **Register Visitor**. Search for a returning visitor by name or contact and choose **Use profile**, or fill in a new profile.
3. Enter the required identity/contact/address/type information, purpose and destination. The person to visit is optional. Selecting **Other** as the visitor type reveals a required field for its specific description (up to 100 characters). The description appears in visitor lists and is restored for returning visitors; reports continue to group these profiles under **Other**. Destinations are selected from the administrator-maintained office dropdown.
4. Choose **Record time-in**. The server supplies the arrival time and recording user. A visitor already inside cannot be registered again until departure is recorded.
5. Search **Active Visitors** and choose **Time Out** when the visitor leaves. Repeating this action preserves the original departure time.
6. Use **Visitor History** and **Reports** to filter by name/contact/purpose/person, arrival date range, visitor type, destination and status. History includes arrival, departure and the recording user; pagination retains filters.

All timestamps and date-based summaries use **Asia/Manila**. The dashboard includes today's arrivals, currently inside, today's departures, this month's arrivals, a selectable seven-day or thirty-day activity chart, all-time visitor type distribution, recent visits and top destinations. Counts represent visits, so a returning visitor can contribute multiple visits. The shared interface includes visitor-history search, desktop sidebar navigation, a collapsible mobile menu and direct arrival/departure actions on the dashboard.

Visitors and offices referenced by visits cannot be deleted. Visit entries in Django Admin are read-only, and visits are created and completed through the daily workflow.

## MySQL

MySQL is the proposed database. The project supports it through environment variables; SQLite remains the local development fallback so the existing local database continues to work. Create an empty MySQL database using `utf8mb4` and an account authorized for that database, then set these variables in the same PowerShell session used to run Django:

```powershell
$env:USE_MYSQL = '1'
$env:DB_NAME = 'vslog_db'
$env:DB_USER = 'your_database_user'
$env:DB_PASSWORD = 'your_database_password'
$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = '3306'
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py createsuperuser
.\venv\Scripts\python.exe manage.py runserver
```

Setting these variables selects a separate database; it does not copy existing SQLite records into MySQL. Back up existing data before a database transfer. MySQL timezone tables must be loaded for Django's timezone-aware date filtering and trend aggregation (for example using the MySQL `mysql_tzinfo_to_sql` utility or the vendor-provided timezone table data).

## Verification

```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test visitors
```

The tests cover registration, returning-visitor reuse, validation, duplicate arrivals, departure recording, filters/report totals, Philippine date boundaries, pagination, authentication, administrative access, CSRF protection and record preservation.

The included configuration is for local development. Bootstrap and Bootstrap Icons are served from `visitors/static/visitors/vendor/`, so the interface does not require a CDN connection. Deployment requires environment-specific security and hosting configuration. Hardware access control, student attendance, visitor accounts and automated identity verification are outside the concept's scope.
