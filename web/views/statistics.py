import collections

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render

from web import models


def statistics(request, project_id):
    """ 统计页面 """
    return render(request, 'statistics.html')


def statistics_priority(request, project_id):
    """ 生成优先级饼图 """
    start = request.GET.get('start')
    end = request.GET.get('end')

    data_dict = collections.OrderedDict()
    for key, text in models.Issues.priority_choices:
        data_dict[key] = {'name': text, 'y': 0}

    results = models.Issues.objects.filter(project_id=project_id, create_datetime__gte=start,
                                           create_datetime__lt=end).values('priority').annotate(ct=Count('id'))

    for item in results:
        data_dict[item['priority']]['y'] = item['ct']

    return JsonResponse({'status': True, 'data': list(data_dict.values())})


def statistics_project_user(request, project_id):
    """ 项目成员每个人被分配的任务数量（问题类型的配比）"""
    start = request.GET.get('start')
    end = request.GET.get('end')

    """
    info = {
        1:{
            name:"武沛齐",
            status:{
                1:0,
                2:1,
                3:0,
                4:0,
                5:0,
                6:0,
                7:0,
            }
        },
        2:{
            name:"王洋",
            status:{
                1:0,
                2:0,
                3:1,
                4:0,
                5:0,
                6:0,
                7:0,
            }
        }
    }
    """
    # 1. 所有项目成员 及 未指派
    all_user_dict = collections.OrderedDict()
    all_user_dict[request.tracer.project.creator.id] = {
        'name': request.tracer.project.creator.username,
        'status': {item[0]: 0 for item in models.Issues.status_code}
    }
    all_user_dict[None] = {
        'name': '未指派',
        'status': {item[0]: 0 for item in models.Issues.status_code}
    }
    user_list = models.ProjectUser.objects.filter(project_id=project_id)
    for item in user_list:
        all_user_dict[item.user_id] = {
            'name': item.user.username,
            'status': {item[0]: 0 for item in models.Issues.status_code}
        }

    # 2. 去数据库获取相关的所有问题
    issues = models.Issues.objects.filter(project_id=project_id, create_datetime__gte=start, create_datetime__lt=end)
    for item in issues:
        if not item.assign:
            all_user_dict[None]['status'][item.status] += 1
        else:
            all_user_dict[item.assign_id]['status'][item.status] += 1

    # 3.获取所有的成员
    categories = [data['name'] for data in all_user_dict.values()]

    # 4.构造字典
    """
    data_result_dict = {
        1:{name:新建,data:[1，2，3，4]},
        2:{name:处理中,data:[3，4，5]},
        3:{name:已解决,data:[]},
        4:{name:已忽略,data:[]},
        5:{name:待反馈,data:[]},
        6:{name:已关闭,data:[]},
        7:{name:重新打开,data:[]},
    }
    """
    data_result_dict = collections.OrderedDict()
    for item in models.Issues.status_code:
        data_result_dict[item[0]] = {'name': item[1], "data": []}

    for key, text in models.Issues.status_code:
        # key=1,text='新建'
        for row in all_user_dict.values():
            count = row['status'][key]
            data_result_dict[key]['data'].append(count)

    context = {
        'status': True,
        'data': {
            'categories': categories,
            'series': list(data_result_dict.values())
        }
    }

    return JsonResponse(context)
