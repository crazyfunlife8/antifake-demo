import os
from pathlib import Path
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

application = get_wsgi_application()

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR / 'project'

application = WhiteNoise(application, max_age=86400)
application.add_files(str(PROJECT_DIR / 'frontPages'), prefix='frontPages')
application.add_files(str(PROJECT_DIR / 'resources'), prefix='resources')
application.add_files(str(PROJECT_DIR / 'generic'), prefix='generic')
