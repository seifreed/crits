from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.targets.views as views
import crits.targets.handlers as handlers
from crits.targets.target import Target
from crits.config.config import CRITsConfig
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.core.source_access import SourceAccess

TSRC = "TestSource"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"

TARGET_EMAIL = "target@example.com"


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
    Target.objects(email_address=TARGET_EMAIL).delete()
    CRITsConfig.drop_collection()


def add_test_target(user):
    return handlers.upsert_target({'email_address': TARGET_EMAIL},
                                  user.username)


class TargetHandlerTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()

    def tearDown(self):
        clean_db()

    def testTargetAdd(self):
        result = add_test_target(self.user)
        self.assertTrue(result['success'])
        self.assertEqual(Target.objects(email_address=TARGET_EMAIL).count(), 1)

    def testTargetGet(self):
        add_test_target(self.user)
        target = Target.objects(email_address=TARGET_EMAIL).first()
        self.assertEqual(target.email_address, TARGET_EMAIL)


class TargetViewTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        add_test_target(self.user)

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/targets/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.targets_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/targets/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.targets_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testTargetsList(self):
        self.req = self.factory.get('/targets/list/')
        self.req.user = self.user
        response = views.targets_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testTargetsjtList(self):
        self.req = self.factory.post('/targets/list/jtlist/', {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.targets_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
