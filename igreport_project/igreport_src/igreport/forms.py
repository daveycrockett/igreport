#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
# encoding=utf-8

from django import forms
from igreport.models import IGReport

class IGReportForm(forms.ModelForm):
    class Meta:
        model = IGReport
