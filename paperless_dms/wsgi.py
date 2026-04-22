import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paperless_dms.settings')
application = get_wsgi_application()
