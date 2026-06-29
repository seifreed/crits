from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.locations.handlers as handlers
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

SAMPLE_MD5 = "d" * 32
SAMPLE_FILENAME = "loc_host.bin"
LOCATION_TYPE = "Destined For"
LOCATION_NAME = "United States"


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
    Sample.objects(md5=SAMPLE_MD5).delete()
    CRITsConfig.drop_collection()


def make_sample():
    sample = Sample()
    sample.md5 = SAMPLE_MD5
    sample.filename = SAMPLE_FILENAME
    sample.add_source(source=TSRC, analyst=TUSER_NAME, tlp='red')
    sample.save(username=TUSER_NAME)
    return sample


class LocationHandlerTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        self.sample = make_sample()

    def tearDown(self):
        clean_db()

    def testLocationAdd(self):
        result = handlers.location_add(str(self.sample.id), 'Sample',
                                       LOCATION_TYPE, LOCATION_NAME, self.user)
        self.assertTrue(result['success'])
        sample = Sample.objects(md5=SAMPLE_MD5).first()
        self.assertEqual(len(sample.locations), 1)
        self.assertEqual(sample.locations[0].location, LOCATION_NAME)

    def testDuplicateLocationRejected(self):
        handlers.location_add(str(self.sample.id), 'Sample', LOCATION_TYPE,
                              LOCATION_NAME, self.user)
        # Adding the same location again should be rejected, not duplicated.
        result = handlers.location_add(str(self.sample.id), 'Sample',
                                       LOCATION_TYPE, LOCATION_NAME, self.user)
        self.assertFalse(result['success'])
        sample = Sample.objects(md5=SAMPLE_MD5).first()
        self.assertEqual(len(sample.locations), 1)
