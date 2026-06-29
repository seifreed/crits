from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.events.views as views
import crits.events.handlers as handlers
from crits.events.event import Event
from crits.config.config import CRITsConfig
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.core.source_access import SourceAccess
from crits.vocabulary.events import EventTypes

TSRC = "TestSource"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"

EVENT_TITLE = "Test Event Title"
EVENT_DESCRIPTION = "Test Event Description"
EVENT_TYPE = EventTypes.PHISHING


def prep_db():
    """
    Prep the DB for the test.
    """

    clean_db()
    # A CRITsConfig is expected to exist at runtime; create one for the tests.
    CRITsConfig().save()
    # Add Source
    add_new_source(TSRC, TUSER_NAME)
    # Ensure the UberAdmin role exists with access to all sources (incl. the
    # one just added) and all ACLs, so the test user can use the web views.
    add_uber_admin_role(drop=False)
    # Add User and grant the admin role.
    user = CRITsUser.create_user(
        username=TUSER_NAME,
        password=TUSER_PASS,
        email=TUSER_EMAIL,
    )
    user.roles = [settings.ADMIN_ROLE]
    user.save()


def clean_db():
    """
    Clean the DB from the test.
    """

    src = SourceAccess.objects(name=TSRC).first()
    if src:
        src.delete()
    user = CRITsUser.objects(username=TUSER_NAME).first()
    if user:
        user.delete()
    Event.objects(title=EVENT_TITLE).delete()
    CRITsConfig.drop_collection()


def add_test_event(user):
    """
    Add a single Event as the test user.
    """

    return handlers.add_new_event(
        EVENT_TITLE,
        EVENT_DESCRIPTION,
        EVENT_TYPE,
        TSRC,
        '',
        '',
        'red',
        None,
        user,
    )


class EventHandlerTests(SimpleTestCase):
    """
    Test Event handlers.
    """

    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        # Warm the ACL cache the way the view decorators do before handlers run.
        self.user.get_access_list(update=True)
        self.user.save()

    def tearDown(self):
        clean_db()

    def testEventAdd(self):
        result = add_test_event(self.user)
        self.assertTrue(result['success'])
        self.assertEqual(Event.objects(title=EVENT_TITLE).count(), 1)

    def testEventGet(self):
        add_test_event(self.user)
        event = Event.objects(title=EVENT_TITLE).first()
        self.assertEqual(event.title, EVENT_TITLE)
        self.assertEqual(event.event_type, EVENT_TYPE)


class EventViewTests(SimpleTestCase):
    """
    Test Event views.
    """

    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        add_test_event(self.user)

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/events/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.events_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/events/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.events_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testEventsList(self):
        self.req = self.factory.get('/events/list/')
        self.req.user = self.user
        response = views.events_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testEventsjtList(self):
        self.req = self.factory.post('/events/list/jtlist/',
                                     {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.events_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
