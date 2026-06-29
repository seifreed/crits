from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.backdoors.views as views
import crits.backdoors.handlers as handlers
from crits.backdoors.backdoor import Backdoor
from crits.config.config import CRITsConfig
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.core.source_access import SourceAccess

TSRC = "TestSource"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"

BACKDOOR_NAME = "Test Backdoor"


def prep_db():
    clean_db()
    CRITsConfig().save()
    add_new_source(TSRC, TUSER_NAME)
    add_uber_admin_role(drop=False)
    user = CRITsUser.create_user(username=TUSER_NAME, password=TUSER_PASS,
                                 email=TUSER_EMAIL)
    user.roles = [settings.ADMIN_ROLE]
    user.save()


def clean_db():
    src = SourceAccess.objects(name=TSRC).first()
    if src:
        src.delete()
    user = CRITsUser.objects(username=TUSER_NAME).first()
    if user:
        user.delete()
    Backdoor.objects(name=BACKDOOR_NAME).delete()
    CRITsConfig.drop_collection()


def add_test_backdoor(user):
    return handlers.add_new_backdoor(BACKDOOR_NAME, source=TSRC,
                                     source_tlp='red', user=user)


class BackdoorHandlerTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()

    def tearDown(self):
        clean_db()

    def testBackdoorAdd(self):
        result = add_test_backdoor(self.user)
        self.assertTrue(result['success'])
        self.assertEqual(Backdoor.objects(name=BACKDOOR_NAME).count(), 1)

    def testBackdoorGet(self):
        add_test_backdoor(self.user)
        backdoor = Backdoor.objects(name=BACKDOOR_NAME).first()
        self.assertEqual(backdoor.name, BACKDOOR_NAME)


class BackdoorViewTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        add_test_backdoor(self.user)

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/backdoors/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.backdoors_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/backdoors/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.backdoors_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testBackdoorsList(self):
        self.req = self.factory.get('/backdoors/list/')
        self.req.user = self.user
        response = views.backdoors_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testBackdoorsjtList(self):
        self.req = self.factory.post('/backdoors/list/jtlist/', {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.backdoors_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
