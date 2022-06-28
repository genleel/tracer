from django import forms

from web import models
from web.forms.bootstrap import BootstrapForm


class IssuesModelForm(BootstrapForm, forms.ModelForm):
    class Meta:
        model = models.Issues
        exclude = ['project', 'creator', 'create_datetime', 'latest_update_datetime']
        widgets = {
            "assign": forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
            "attention": forms.SelectMultiple(
                attrs={'class': 'selectpicker', 'data-live-search': 'true', 'data-actions-box': 'true'}),
            "parent": forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        }

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 处理数据初始化
        # 1.获取当前项目的所有数据类型
        self.fields['issues_type'].choices = models.IssuesType.objects.filter(
            project=request.tracer.project).values_list('id', 'title')

        # 2.获取当前项目的所有模块
        module_list = [("", "没有选择任何项"), ]
        module_object_list = models.Module.objects.filter(
            project=request.tracer.project).values_list('id', 'title')
        module_list.extend(module_object_list)
        self.fields['module'].choices = module_list

        # 3.指派和关注者
        total_user_list = [(request.tracer.project.creator_id, request.tracer.project.creator.username),]
        project_user_list = models.ProjectUser.objects.filter(project=request.tracer.project)\
            .values_list('user_id', 'user__username')

        total_user_list.extend(project_user_list)

        self.fields['assign'].choices = [("", "没有选择任何项")] + total_user_list
        self.fields['attention'].choices = total_user_list

        # 5.父问题
        parent_list = [("", "没有选择任何项")]
        parent_object_list = models.Issues.objects.filter(project=request.tracer.project).values_list('id', 'subject')
        parent_list.extend(parent_object_list)
        self.fields['parent'].choices = parent_list


class IssuesReplyModelForm(forms.ModelForm):
    class Meta:
        model = models.IssuesReply
        fields = ['content', 'reply']


class InviteModelForm(forms.ModelForm):
    class Meta:
        model = models.ProjectInvite
        fields = ['period', 'count']