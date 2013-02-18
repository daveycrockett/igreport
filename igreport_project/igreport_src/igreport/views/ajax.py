import re
import json
from django.utils import simplejson
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from rapidsms.contrib.locations.models import Location, LocationType
from igreport.models import IGReport, Category, Comment

def ajax_success(msg=None, js_=None):
    if msg is None:
        msg = 'OK'

    if js_ is None:
        js = '{error:false, msg:"%s"}' % msg
    else:
        js = '{error:false, msg:"%s", %s}' % (msg, js_)
    return HttpResponse(js, mimetype='text/plain', status=200)

@login_required
@require_GET
@never_cache
def get_report(request, report_id):

    r = get_object_or_404(IGReport, pk=report_id)

    js = {
        'accused': r.subject if r.subject else '',
        'report': r.report if r.report else '',
        'amount_ff': r.amount_freeform if r.amount_freeform else '',
        'amount': str( int(r.amount) ) if r.amount else '',
        'sc_ff': r.subcounty_freeform if r.subcounty_freeform else '',
        'subcounty_id': r.subcounty_id if r.subcounty_id else '',
        'district_id': r.district_id if r.district_id else '',
        'when_ff': r.when_freeform if r.when_freeform else '',
        'when': r.when_datetime.strftime('%m/%d/%Y') if r.when_datetime else '',
        'date': r.datetime.strftime('%d/%m/%Y %H:%M'),
        'sender': r.connection.identity,
    }
    js_rpt = simplejson.dumps(js)

    ''' get districts '''
    objs = Location.objects.filter(type='district').order_by('name')
    l = [ '{id:%s,name:%s}' % (d.id, json.dumps(d.name)) for d in objs ]
    js_districts = '[%s]' % ','.join(l)

    ''' get sub-counties '''
    objs = Location.objects.filter(type='sub_county').order_by('name')
    l = [ '{id:%s,name:%s}' % (d.id, json.dumps(d.name)) for d in objs ]
    js_subcty = '[%s]' % ','.join(l)

    ''' the selected categories '''
    curr_categories = [c.id for c in r.categories.all()]

    ''' all categories '''
    objs = Category.objects.all()
    l = list()
    
    for c in objs:
        checked='false'
        if curr_categories.__contains__(c.id):
            checked = 'true'
        l.append( '{id:%s,name:%s,checked:%s}' % (c.id, json.dumps(c.name), checked) )

    js_cat = '[%s]' % ','.join(l)
    
    ''' comments '''
    objs = Comment.objects.filter(report=r)
    l = [ '{user:%s,date:%s,comment:%s}' % (json.dumps(c.user.username), json.dumps(c.datetime.strftime('%d/%m/%Y')), json.dumps(c.comment)) for c in objs ]
    js_comments = '[%s]' % ','.join(l)
    
    js_text = 'res:{ rpt:%s,dist:%s,scty:%s,cat:%s,comm:%s }' % ( js_rpt, js_districts, js_subcty, js_cat, js_comments )
    
    return ajax_success('OK', js_text)
