from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.domains.views as views
import crits.domains.handlers as handlers
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.core.source_access import SourceAccess

TSRC = "TestSource"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"
TUSER_ROLE = "Administrator"

DOM_REF = ""
DOM_SRC = TSRC
DOM_METH = ""
DOMAIN = "example.com"

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


class DomainHandlerTests(SimpleTestCase):
    """
    Test Domain Handlers
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

    def testDomainAdd(self):
        data = {
                'source_reference': DOM_REF,
                'source_name': DOM_SRC,
                'source_method': DOM_METH,
                'source_tlp': 'red',
                'domain': DOMAIN,
                }
        request = self.factory.post('/domains/add/', data)
        request.user = self.user
        errors = []
        (result, errors, retVal) = handlers.add_new_domain(data, request, errors)



class DomainViewTests(SimpleTestCase):
    """
    Test Domain Views
    """

    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        # Warm the ACL cache the way the view decorators do before handlers run.
        self.user.get_access_list(update=True)
        self.user.save()
        # Add a test domain
        data = {
                'source_reference': DOM_REF,
                'source_name': DOM_SRC,
                'source_method': DOM_METH,
                'source_tlp': 'red',
                'domain': DOMAIN,
                }
        request = self.factory.post('/domains/add/', data)
        request.user = self.user
        errors = []
        (result, errors, retVal) = handlers.add_new_domain(data, request, errors)

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/domains/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.domains_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/domains/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.domains_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testDomainsList(self):
        self.req = self.factory.get('/domains/list/')
        self.req.user = self.user
        response = views.domains_listing(self.req)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"#domain_listing" in response.content)

    def testDomainsjtList(self):
        self.req = self.factory.post('/domains/list/jtlist/',
                                     {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.domains_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
