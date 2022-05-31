from django import forms
from django.core.exceptions import ValidationError

from web import models
from web.forms.bootstrap import BootstrapForm
from web.forms.widgets import ColorRadioSelect


class ProjectModelForm(BootstrapForm, forms.ModelForm):
    bootstrap_class_exclude = ['color']

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    class Meta:
        model = models.Project
        fields = ['name', 'color', 'desc']
        # 重写插件
        widgets = {
            'desc': forms.Textarea,
            'color': ColorRadioSelect(attrs={'class': 'color-radio'}),
        }

    def clean_name(self):
        """项目校验"""
        name = self.cleaned_data['name']
        # 项目名不可重复
        exists = models.Project.objects.filter(name=name, creator=self.request.tracer.user).exists()
        if exists:
            raise ValidationError('项目名已存在')
        # 是否还有额度
        project_num = self.request.tracer.price_policy.project_num

        count = models.Project.objects.filter(creator=self.request.tracer.user).count()
        if count >= project_num:
            raise ValidationError('项目个数超额，请升级套餐')

        return name
