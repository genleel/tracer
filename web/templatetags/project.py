from django.template import Library
from django.urls import reverse

from web import models

register = Library()


@register.inclusion_tag('inclusion/all_project_list.html')
def all_project_list(request):
    # 创建的项目
    my_project_list = models.Project.objects.filter(creator=request.tracer.user)
    # 参与的项目
    join_project_list = models.ProjectUser.objects.filter(user=request.tracer.user)

    return {'my': my_project_list, 'join': join_project_list, 'request': request}


@register.inclusion_tag('inclusion/manage_menu_list.html')
def manage_menu_list(request):
    data_list = [
        {'title': '概览', 'url': reverse('dashboard', kwargs={'project_id': request.tracer.project.id})},
        {'title': '问题', 'url': reverse('issues', kwargs={'project_id': request.tracer.project.id})},
        {'title': '统计', 'url': reverse('statistics', kwargs={'project_id': request.tracer.project.id})},
        {'title': 'wiki', 'url': reverse('wiki', kwargs={'project_id': request.tracer.project.id})},
        {'title': '文件', 'url': reverse('file', kwargs={'project_id': request.tracer.project.id})},
        {'title': '设置', 'url': reverse('setting', kwargs={'project_id': request.tracer.project.id})},
    ]
    # 设置选中状态
    for item in data_list:
        if request.path_info.startswith(item['url']):
            item['class'] = 'active'

    return {'data_list': data_list}

