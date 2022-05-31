import os
import sys
import django

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tracer.settings")
django.setup()  # os.environ['DJANGO_SETTINGS_MODULE']

from web import models

django.setup()

models.UserInfo.objects.create(username='zhangsan', email='zhangsan@qq.com', mobile_phone='15045692583',
                               password=12345678)
