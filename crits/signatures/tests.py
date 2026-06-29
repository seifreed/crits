from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

from . import views
import crits.signatures.handlers as handlers
from crits.signatures.signature import Signature
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.signatures.handlers import add_new_signature_type
from crits.core.source_access import SourceAccess

TSRC = "TestSource"
TDT = "Yara"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"
TUSER_ROLE = "Administrator"

SIGNATURE_TITLE = "Test Signature Title"
SIGNATURE_DESCRIPTION = "Test Signature Description"
SIGNATURE_DATA = "Test Signature Data"

def prep_db():
    """
    Prep database for test.
    """

    clean_db()
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
    # Add Data Type
    add_new_signature_type(TDT, TUSER_NAME)

def clean_db():
    """
    Clean database for test.
    """

    src = SourceAccess.objects(name=TSRC).first()
    if src:
        src.delete()
    user = CRITsUser.objects(username=TUSER_NAME).first()
    if user:
        user.delete()
    # Drop signatures so documents don't leak across tests (each add creates a
    # new versioned Signature, which otherwise pollutes title lookups).
    Signature.objects(title=SIGNATURE_TITLE).delete()


class SignatureHandlerTests(SimpleTestCase):
    """
    Test Signature Handlers
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

    def testSignatureAdd(self):
        title = SIGNATURE_TITLE
        description = SIGNATURE_DESCRIPTION
        data = SIGNATURE_DATA
        data_type = TDT
        source_name = TSRC
        user = self.user
        (status) = handlers.handle_signature_file(data, source_name, user, description, title, data_type, source_tlp='red')

    def testSignatureCampaign(self):
        # Regression for crits#732: a campaign on upload must attach.
        handlers.handle_signature_file(SIGNATURE_DATA, TSRC, self.user,
                                       SIGNATURE_DESCRIPTION, SIGNATURE_TITLE,
                                       TDT, source_tlp='red',
                                       campaign='TestCampaign')
        sig = Signature.objects(title=SIGNATURE_TITLE).first()
        self.assertIn('TestCampaign', [c.name for c in sig.campaign])


class SignatureViewTests(SimpleTestCase):
    """
    Test Signature Views
    """

    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        # Warm the ACL cache the way the view decorators do before handlers run.
        self.user.get_access_list(update=True)
        self.user.save()
        # Add a test signature
        title = SIGNATURE_TITLE
        description = SIGNATURE_DESCRIPTION
        data = SIGNATURE_DATA
        data_type = TDT
        source_name = TSRC
        user = self.user
        (status) = handlers.handle_signature_file(data, source_name, user, description, title, data_type, source_tlp='red')

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/signatures/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.signatures_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/signatures/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.signatures_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testSignaturesList(self):
        self.req = self.factory.get('/signatures/list/')
        self.req.user = self.user
        response = views.signatures_listing(self.req)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"#signature_listing" in response.content)

    def testSignaturesjtList(self):
        self.req = self.factory.post('/signatures/list/jtlist/',
                                     {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.signatures_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
