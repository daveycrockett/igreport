#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
# encoding=utf-8

from django.contrib.auth.models import User
from django.test import TestCase
from igreport.models import IGReport
from rapidsms.contrib.locations.models import Location, LocationType
from rapidsms.messages import IncomingMessage
from rapidsms.models import Contact, Backend, Connection
from rapidsms_httprouter.models import Message
from rapidsms_httprouter.router import get_router
from script.models import ScriptProgress, ScriptSession, ScriptResponse, Script
from script.signals import script_progress_was_completed
from script.utils.outgoing import check_progress
from django.core.management import call_command
import datetime

class ModelTest(TestCase):  # pragma: no cover

    def setUp(self):
        """
        Create a dummy connection
        """

        self.backend = Backend.objects.create(name='test')
        self.connection = Connection.objects.create(identity='8675309', backend=self.backend)
        self.user, _ = User.objects.get_or_create(username="admin")
        self.router = get_router()

        # create test contact
        self.connection.contact = Contact.objects.create(name='Anonymous User')
        self.connection.save()

        Location.objects.create(name="Busia", type=LocationType.objects.create(name="district", slug="district"))
        Location.objects.create(name="Gwinnett", type=LocationType.objects.create(name="sub_county", slug="sub_county"))

        call_command('create_hotline_script')

    def fake_incoming(self, message, connection):
        self.router.handle_incoming(connection.backend.name, connection.identity, message)

    def spoof_incoming_obj(self, message, connection=None):
        if connection is None:
            connection = Connection.objects.all()[0]
        incomingmessage = IncomingMessage(connection, message)
        incomingmessage.db_message = Message.objects.create(direction='I', connection=Connection.objects.all()[0], text=message)
        return incomingmessage

    def fake_script_dialog(self, script_prog, responses, emit_signal=True):
        connection = script_prog.connection
        script = script_prog.script
        ss = ScriptSession.objects.create(script=script, connection=connection, start_time=datetime.datetime.now())
        for poll_name, resp in responses:
            poll = script.steps.get(poll__name=poll_name).poll
            poll.process_response(self.spoof_incoming_obj(resp))
            resp = poll.responses.all().order_by('-date')[0]
            ScriptResponse.objects.create(session=ss, response=resp)
        ss.end_time = datetime.datetime.now()
        ss.save()

        if emit_signal:
            script_progress_was_completed.send(connection=connection, sender=script_prog)
        return ss

    def test_igreport(self):

        report = 'there are many snakes in BUSIA'
        name = 'SNAKES, MAN!'
        subcounty = 'gwinnett somehow'
        when = '7 days ago'

        # fake report
        self.fake_incoming(report, self.connection)
        # make sure a script progress was created
        # get a response
        self.assertEquals(ScriptProgress.objects.count(), 1)
        script_prog = ScriptProgress.objects.all()[0]

        self.fake_script_dialog(script_prog, [('hotline_name', name), \
            ('hotline_district', 'busia'), \
            ('hotline_subcounty', subcounty), \
            ('hotline_when', when)])

        ig_report = IGReport.objects.all()[0]
        self.assertEquals(ig_report.report, report)
        self.assertEquals(ig_report.name, name)
        self.assertEquals(ig_report.subcounty_freeform, subcounty)
        self.assertEquals(ig_report.subcounty, Location.objects.get(type__name='sub_county'))
        self.assertEquals(ig_report.district, Location.objects.get(type__name='district'))
        self.assertEquals(ig_report.when_freeform, when)
