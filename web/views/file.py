import json

from django.forms import model_to_dict
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from web import models
from web.forms.file import FolderModelForm, FileModelForm

from utils.tencent.cos import delete_file, delete_file_list, credential


# http://127.0.0.1:8002/manage/1/file/
# http://127.0.0.1:8002/manage/1/file/?folder=1
def file(request, project_id):
    """ 文件列表 & 添加文件夹 """

    parent_object = None
    folder_id = request.GET.get('folder', "")
    if folder_id.isdecimal():
        parent_object = models.FileRepository.objects.filter(id=int(folder_id), file_type=2,
                                                             project=request.tracer.project).first()

    # GET 查看页面
    if request.method == "GET":

        breadcrumb_list = []
        parent = parent_object
        while parent:
            # breadcrumb_list.insert(0, {'id': parent.id, 'name': parent.name})
            breadcrumb_list.insert(0, model_to_dict(parent, ['id', 'name']))
            parent = parent.parent

        # 当前目录下所有的文件 & 文件夹获取到即可
        queryset = models.FileRepository.objects.filter(project=request.tracer.project)
        if parent_object:
            # 进入了某目录
            file_object_list = queryset.filter(parent=parent_object).order_by('-file_type')
        else:
            # 根目录
            file_object_list = queryset.filter(parent__isnull=True).order_by('-file_type')
        form = FolderModelForm(request, parent_object)

        context = {
            'form': form,
            "file_object_list": file_object_list,
            "breadcrumb_list": breadcrumb_list,
            'folder_object': parent_object
        }
        return render(request, 'file.html', context)

    # POST 添加文件夹 & 文件夹的修改
    fid = request.POST.get('fid', '')
    edit_object = None
    if fid.isdecimal():
        edit_object = models.FileRepository.objects.filter(id=int(fid), file_type=2,
                                                           project=request.tracer.project).first()

    if edit_object:
        form = FolderModelForm(request, parent_object, data=request.POST, instance=edit_object)
    else:
        form = FolderModelForm(request, parent_object, data=request.POST)

    if form.is_valid():
        form.instance.project = request.tracer.project
        form.instance.file_type = 2
        form.instance.update_user = request.tracer.user
        form.instance.parent = parent_object
        form.save()
        return JsonResponse({'status': True})

    return JsonResponse({'status': False, 'error': form.errors})


def file_delete(request, project_id):
    """ 删除文件 数据库 cos 空间容量更新 """
    fid = request.GET.get('fid')
    delete_object = models.FileRepository.objects.filter(id=fid, project=request.tracer.project).first()

    if delete_object.file_type == 1:  # 文件
        # 更新已使用空间
        request.tracer.project.use_space -= delete_object.file_size
        request.tracer.project.save()
        # cos中删除
        delete_file(request.tracer.project.bucket, request.tracer.project.region, delete_object.key)
        # 在数据库中删除
        delete_object.delete()

        return JsonResponse({'status': True})

    # 处理文件夹
    total_size = 0
    folder_list = [delete_object, ]
    key_list = []
    for folder in folder_list:
        child_list = models.FileRepository.objects.filter(project=request.tracer.project, parent=folder) \
            .order_by('-file_type')
        for child in child_list:
            if child.file_type == 2:
                folder_list.append(child)
            else:
                total_size += child.file_size
                key_list.append({"Key": child.key})

    if key_list:
        delete_file_list(request.tracer.project.bucket, request.tracer.project.region, key_list)
    if total_size:
        request.tracer.project.use_space -= total_size
        request.tracer.project.save()
    delete_object.delete()

    return JsonResponse({'status': True})


@csrf_exempt
def cos_credential(request, project_id):
    """ 获取cos上传临时凭证 """
    file_list = json.loads(request.body.decode('utf-8'))
    # 单文件限制
    per_file_limit = request.tracer.price_policy.per_file_size * 1024 * 1024

    total_size = 0
    for item in file_list:
        if item['size'] > per_file_limit:
            msg = '单文件超出限制（最大{}M），文件：{}'.format(request.tracer.price_policy.per_file_size, item['name'])
            return JsonResponse({'status': False, 'error': msg})
        total_size += item['size']

    # 总容量限制
    total_file_limit = request.tracer.price_policy.project_space * 1024 * 1024 * 1024
    if request.tracer.project.use_space + total_size > total_file_limit:
        msg = '总容量超出限制'
        return JsonResponse({'status': False, 'error': msg})

    # 容量限制
    data_dict = credential(request.tracer.project.bucket, request.tracer.project.region)
    return JsonResponse({'status': True, 'data': data_dict})


@csrf_exempt
def file_post(request, project_id):
    """ 文件写入到数据库 """
    form = FileModelForm(request, data=request.POST)

    if form.is_valid():
        # 校验通过：写入数据库
        data_dict = form.cleaned_data
        data_dict.pop('etag')
        data_dict.update({'project': request.tracer.project, 'file_type': 1, 'update_user': request.tracer.user})
        instance = models.FileRepository.objects.create(**data_dict)

        # 更新已使用空间
        request.tracer.project.use_space += data_dict['file_size']
        request.tracer.project.save()

        result = {
            'id': instance.id,
            'name': instance.name,
            'file_size': instance.file_size,
            'username': instance.update_user.username,
            'datetime': instance.update_datetime.strftime("%Y年%m月%d日 %H:%M"),
            'file_type': instance.get_file_type_display(),
            'download_url': reverse('file_download', kwargs={"project_id": project_id, "file_id": instance.id})
        }

        return JsonResponse({'status': True, 'data': result})

    return JsonResponse({'status': False, 'data': '文件错误'})


def file_download(request, project_id, file_id):
    """ 下载文件 """
    # cos获取文件内容
    import requests

    file_object = models.FileRepository.objects.filter(id=file_id, project_id=project_id).first()
    res = requests.get(file_object.file_path)
    # 大文件分块处理
    data = res.iter_content()

    # 提示下载框
    response = HttpResponse(data, content_type="application/octet-stream")
    from django.utils.encoding import escape_uri_path

    # 响应头
    response['Content-Disposition'] = "attachment; filename={}".format(escape_uri_path(file_object.name))

    return response
