import os
import sys
from pathlib import Path
from types import SimpleNamespace

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
import django
django.setup()
from django.test import RequestFactory
from django.urls import resolve
from django.contrib.messages.storage.fallback import FallbackStorage

output = root / '.preview/rendered'
output.mkdir(exist_ok=True)
for name, url in [('dashboard', '/dashboard/'), ('month', '/dashboard/?period=month'),
                  ('registration', '/register-visitor/'), ('active', '/active-visitors/'),
                  ('history', '/visitor-history/'), ('reports', '/reports/'), ('login', '/login/')]:
    request = RequestFactory().get(url)
    request.user = SimpleNamespace(is_authenticated=name != 'login', is_staff=True,
                                  username='Campus Admin', first_name='Alex', get_full_name=lambda: 'Alex Santos')
    request.session = {}
    request._messages = FallbackStorage(request)
    request.resolver_match = resolve(request.path)
    response = request.resolver_match.func(request)
    assert response.status_code == 200, (name, response.status_code)
    html = response.content.decode('utf-8').replace('/static/', (root / 'visitors/static').as_uri() + '/')
    (output / f'{name}.html').write_text(html, encoding='utf-8')
    print(f'{name}: rendered successfully')
