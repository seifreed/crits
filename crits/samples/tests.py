from hashlib import md5

from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.samples.views as views
import crits.samples.handlers as handlers
from crits.samples.sample import Sample
from crits.config.config import CRITsConfig
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.core.source_access import SourceAccess

TSRC = "TestSource"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"

SAMPLE_FILENAME = "test_sample.bin"
SAMPLE_DATA = b"MZ\x90\x00 this is a fake sample binary for testing"
SAMPLE_MD5 = md5(SAMPLE_DATA, usedforsecurity=False).hexdigest()


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
    Sample.objects(md5=SAMPLE_MD5).delete()
    CRITsConfig.drop_collection()


def add_test_sample(user):
    """
    Add a single sample as the test user, returning its MD5.
    """

    return handlers.handle_file(
        SAMPLE_FILENAME,
        SAMPLE_DATA,
        TSRC,
        user=user,
        source_method='',
        source_reference='',
        source_tlp='red',
    )


class SampleHandlerTests(SimpleTestCase):
    """
    Test Sample handlers.
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

    def testSampleAdd(self):
        result = add_test_sample(self.user)
        self.assertEqual(result, SAMPLE_MD5)
        self.assertEqual(Sample.objects(md5=SAMPLE_MD5).count(), 1)

    def testSampleGet(self):
        add_test_sample(self.user)
        sample = Sample.objects(md5=SAMPLE_MD5).first()
        self.assertEqual(sample.md5, SAMPLE_MD5)
        self.assertEqual(sample.filename, SAMPLE_FILENAME)
        # The fake binary starts with "MZ", so PE detection should fire.
        self.assertTrue(sample.is_pe())


class SampleViewTests(SimpleTestCase):
    """
    Test Sample views.
    """

    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        add_test_sample(self.user)

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/samples/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.samples_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/samples/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.samples_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testSamplesList(self):
        self.req = self.factory.get('/samples/list/')
        self.req.user = self.user
        response = views.samples_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testSamplesjtList(self):
        self.req = self.factory.post('/samples/list/jtlist/',
                                     {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.samples_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
