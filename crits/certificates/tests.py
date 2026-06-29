from hashlib import md5

from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.certificates.views as views
import crits.certificates.handlers as handlers
from crits.certificates.certificate import Certificate
from crits.config.config import CRITsConfig
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.core.source_access import SourceAccess

TSRC = "TestSource"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"

CERT_FILENAME = "test.crt"
CERT_DATA = b"-----BEGIN CERTIFICATE-----\nMIIBfakecertdata\n-----END CERTIFICATE-----\n"
CERT_MD5 = md5(CERT_DATA, usedforsecurity=False).hexdigest()


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
    Certificate.objects(md5=CERT_MD5).delete()
    CRITsConfig.drop_collection()


def add_test_cert(user):
    return handlers.handle_cert_file(CERT_FILENAME, CERT_DATA, TSRC, user=user,
                                     method='', reference='', tlp='red')


class CertificateHandlerTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()

    def tearDown(self):
        clean_db()

    def testCertAdd(self):
        result = add_test_cert(self.user)
        self.assertTrue(result['success'])
        self.assertEqual(Certificate.objects(md5=CERT_MD5).count(), 1)

    def testCertCampaign(self):
        # Regression for crits#732: a campaign on upload must attach.
        result = handlers.handle_cert_file(CERT_FILENAME, CERT_DATA, TSRC,
                                           user=self.user, method='',
                                           reference='', tlp='red',
                                           campaign='TestCampaign')
        self.assertTrue(result['success'])
        cert = Certificate.objects(md5=CERT_MD5).first()
        self.assertIn('TestCampaign', [c.name for c in cert.campaign])

    def testCertGet(self):
        add_test_cert(self.user)
        cert = Certificate.objects(md5=CERT_MD5).first()
        self.assertEqual(cert.md5, CERT_MD5)
        self.assertEqual(cert.filename, CERT_FILENAME)


class CertificateViewTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        add_test_cert(self.user)

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/certificates/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.certificates_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/certificates/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.certificates_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testCertsList(self):
        self.req = self.factory.get('/certificates/list/')
        self.req.user = self.user
        response = views.certificates_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testCertsjtList(self):
        self.req = self.factory.post('/certificates/list/jtlist/', {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.certificates_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
