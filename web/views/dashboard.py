#!/usr/bin/env python
# -*- coding:utf-8 -*-
import time
import datetime
import collections
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count
from django.db.models import Count
from web import models

def dashboard(request, project_id):
    """ 概览 """
    status_dict = collections.OrderedDict()
    for key, text in models.Issues.status_code:
        status_dict[key] = {'text': text, 'count': 0}

    issues_data = models.Issues.objects.filter(project_id=project_id).values('status').annotate(ct=Count('id'))
    for item in issues_data:
        status_dict[item['status']]['count'] = item['ct']

    user_list = models.ProjectUser.objects.filter(project_id=project_id).values('user_id', 'user__username')

    top_ten_object = models.Issues.objects.filter(project_id=project_id, assign__isnull=False).order_by('-id')[:10]

    context = {
        'status_dict': status_dict,
        'user_list': user_list,
        'top_ten_object': top_ten_object,
    }

    return render(request, 'dashboard.html', context)


def issues_chart(request, project_id):
    """ 生成highcharts """
    today = datetime.datetime.now().date()
    date_dict = collections.OrderedDict()
    for i in range(0, 30):
        date = today - datetime.timedelta(days=i)
        date_dict[date.strftime("%Y-%m-%d")] = [time.mktime(date.timetuple()) * 1000, 0]

    # select xxxx,1 as ctime from xxxx
    # select id,name,email from table;
    # select id,name, strftime("%Y-%m-%d",create_datetime) as ctime from table;
    # "DATE_FORMAT(web_transaction.create_datetime,'%%Y-%%m-%%d')"
    result = models.Issues.objects.filter(project_id=project_id,
                                          create_datetime__gte=today - datetime.timedelta(days=30)).extra(
        select={'ctime': "DATE_FORMAT(web_issues.create_datetime,'%%Y-%%m-%%d')"}).values('ctime').annotate(ct=Count('id'))

    for item in result:
        date_dict[item['ctime']][1] = item['ct']

    return JsonResponse({'status': True, 'data': list(date_dict.values())})
