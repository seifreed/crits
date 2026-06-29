from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.raw_data.views as views
import crits.raw_data.handlers as handlers
from crits.raw_data.raw_data import RawData
from crits.raw_data.handlers import add_new_raw_data_type
from crits.config.config import CRITsConfig
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.core.source_access import SourceAccess

TSRC = "TestSource"
TDT = "Text"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"

RD_TITLE = "Test RawData Title"
RD_DATA = "line one\nline two\nline three\n"


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
    # RawData requires a known data type.
    add_new_raw_data_type(TDT, TUSER_NAME)


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
    RawData.objects(title=RD_TITLE).delete()
    CRITsConfig.drop_collection()


def add_test_raw_data(user):
    """
    Add a single RawData document as the test user.
    """

    return handlers.handle_raw_data_file(
        RD_DATA,
        TSRC,
        user=user,
        title=RD_TITLE,
        data_type=TDT,
        method='',
        reference='',
        tlp='red',
    )


class RawDataHandlerTests(SimpleTestCase):
    """
    Test RawData handlers.
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

    def testRawDataAdd(self):
        result = add_test_raw_data(self.user)
        self.assertTrue(result['success'])
        self.assertEqual(RawData.objects(title=RD_TITLE).count(), 1)

    def testRawDataCampaign(self):
        # Regression for crits#732: a campaign on upload must attach.
        result = handlers.handle_raw_data_file(
            RD_DATA, TSRC, user=self.user, title=RD_TITLE, data_type=TDT,
            method='', reference='', tlp='red', campaign='TestCampaign')
        self.assertTrue(result['success'])
        rd = RawData.objects(title=RD_TITLE).first()
        self.assertIn('TestCampaign', [c.name for c in rd.campaign])

    def testRawDataGet(self):
        add_test_raw_data(self.user)
        rd = RawData.objects(title=RD_TITLE).first()
        self.assertEqual(rd.title, RD_TITLE)
        self.assertEqual(rd.data_type, TDT)
        self.assertEqual(rd.data, RD_DATA)


class RawDataViewTests(SimpleTestCase):
    """
    Test RawData views.
    """

    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        add_test_raw_data(self.user)

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/raw_data/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.raw_data_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/raw_data/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.raw_data_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testRawDataList(self):
        self.req = self.factory.get('/raw_data/list/')
        self.req.user = self.user
        response = views.raw_data_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testRawDatajtList(self):
        self.req = self.factory.post('/raw_data/list/jtlist/',
                                     {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.raw_data_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
