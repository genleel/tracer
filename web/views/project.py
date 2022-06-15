import time

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect

from utils.tencent.cos import create_bucket
from web import models
from web.forms.project import ProjectModelForm


def project_list(request):
    """项目列表"""
    if request.method == 'GET':

        project_dict = {'star': [], 'my': [], 'join': []}
        # 创建的项目
        my_project_list = models.Project.objects.filter(creator=request.tracer.user)
        for item in my_project_list:
            if item.star:
                project_dict['star'].append({'value': item, 'type': 'my'})
            else:
                project_dict['my'].append(item)

        # 参与的项目
        join_project_list = models.ProjectUser.objects.filter(user=request.tracer.user)
        for item in join_project_list:
            if item.star:
                project_dict['star'].append({'value': item.project, 'type': 'join'})
            else:
                project_dict['join'].append(item.project)

        form = ProjectModelForm(request)
        return render(request, 'project_list.html', {'form': form, 'project_dict': project_dict})

    form = ProjectModelForm(request, data=request.POST)
    if form.is_valid():
        # 验证通过
        # 1.为项目创建一个桶
        name = form.cleaned_data['name']
        bucket = "{}-1305880705".format(name)
        region = 'ap-beijing'
        create_bucket(bucket, region)

        form.instance.bucket = bucket
        form.instance.region = region
        form.instance.creator = request.tracer.user

        # 2.创建项目
        instance = form.save()

        # 3.项目初始化问题类型
        issues_type_object_list = []
        for item in models.IssuesType.PROJECT_INIT_LIST:
            issues_type_object_list.append(models.IssuesType(project=instance, title=item))
        models.IssuesType.objects.bulk_create(issues_type_object_list)

        return JsonResponse({'status': True})

    return JsonResponse({'status': False, 'error': form.errors})


def project_star(request, project_type, project_id):
    """ 星标项目 """
    if project_type == 'my':
        models.Project.objects.filter(id=project_id, creator=request.tracer.user).update(star=True)
        return redirect('project_list')

    if project_type == 'join':
        models.ProjectUser.objects.filter(project_id=project_id, user=request.tracer.user).update(star=True)
        return redirect('project_list')

    return HttpResponse('请求错误')


def project_unstar(request, project_type, project_id):
    """ 取消星标 """
    if project_type == 'my':
        models.Project.objects.filter(id=project_id, creator=request.tracer.user).update(star=False)
        return redirect('project_list')

    if project_type == 'join':
        models.ProjectUser.objects.filter(project_id=project_id, user=request.tracer.user).update(star=False)
        return redirect('project_list')

    return HttpResponse('请求错误')
