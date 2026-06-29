from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.objects.handlers as handlers
from crits.samples.sample import Sample
from crits.config.config import CRITsConfig
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.core.source_access import SourceAccess
from crits.vocabulary.objects import ObjectTypes

TSRC = "TestSource"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"

SAMPLE_MD5 = "b" * 32
SAMPLE_FILENAME = "obj_host.bin"
OBJ_TYPE = ObjectTypes.STRING
OBJ_VALUE = "test object value"


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


class ObjectHandlerTests(SimpleTestCase):
    """
    Test object handlers (adding an object to a TLO). Regression coverage for
    add_object's tlp/user signature.
    """

    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        self.sample = make_sample()

    def tearDown(self):
        clean_db()

    def testAddObject(self):
        result = handlers.add_object('Sample', str(self.sample.id), OBJ_TYPE,
                                     TSRC, '', '', 'red', self.user,
                                     value=OBJ_VALUE)
        self.assertTrue(result['success'])
        sample = Sample.objects(md5=SAMPLE_MD5).first()
        self.assertEqual(len(sample.obj), 1)
        self.assertEqual(sample.obj[0].value, OBJ_VALUE)

    def testAddObjectViaHandler(self):
        # add_new_handler_object is the bulk/UI entry point fixed in crits#1014:
        # it must pass tlp and the user object (not the analyst string).
        data = {
            'object_type': OBJ_TYPE,
            'value': OBJ_VALUE,
            'source': TSRC,
            'method': '',
            'reference': '',
            'tlp': 'red',
            'otype': 'Sample',
            'oid': str(self.sample.id),
            'add_indicator': False,
        }
        request = self.factory.post('/objects/add/', data)
        request.user = self.user
        result, retVal = handlers.add_new_handler_object(
            data, None, request, obj=self.sample)
        self.assertTrue(result)

    def testAddObjectWithIndicator(self):
        # Regression for crits#1068: adding an object with "add indicator"
        # checked must thread the source through to handle_indicator_ind
        # instead of failing with "Missing source information".
        result = handlers.add_object('Sample', str(self.sample.id), OBJ_TYPE,
                                     TSRC, '', '', 'red', self.user,
                                     value=OBJ_VALUE, add_indicator=True)
        self.assertTrue(result['success'])
        self.assertNotIn('Missing source information',
                         result.get('message', ''))
