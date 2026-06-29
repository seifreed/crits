from hashlib import md5

from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.pcaps.views as views
import crits.pcaps.handlers as handlers
from crits.pcaps.pcap import PCAP
from crits.config.config import CRITsConfig
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.core.source_access import SourceAccess

TSRC = "TestSource"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"

PCAP_FILENAME = "test.pcap"
# Real libpcap magic followed by some bytes so it looks like a capture.
PCAP_DATA = b"\xd4\xc3\xb2\xa1\x02\x00\x04\x00" + b"\x00" * 16 + b"payload"
PCAP_MD5 = md5(PCAP_DATA, usedforsecurity=False).hexdigest()


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
    PCAP.objects(md5=PCAP_MD5).delete()
    CRITsConfig.drop_collection()


def add_test_pcap(user):
    """
    Add a single PCAP as the test user.
    """

    return handlers.handle_pcap_file(
        PCAP_FILENAME,
        PCAP_DATA,
        TSRC,
        user=user,
        method='',
        reference='',
        tlp='red',
    )


class PcapHandlerTests(SimpleTestCase):
    """
    Test PCAP handlers.
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

    def testPcapAdd(self):
        result = add_test_pcap(self.user)
        self.assertTrue(result['success'])
        self.assertEqual(PCAP.objects(md5=PCAP_MD5).count(), 1)

    def testPcapGet(self):
        add_test_pcap(self.user)
        pcap = PCAP.objects(md5=PCAP_MD5).first()
        self.assertEqual(pcap.md5, PCAP_MD5)
        self.assertEqual(pcap.filename, PCAP_FILENAME)


class PcapViewTests(SimpleTestCase):
    """
    Test PCAP views.
    """

    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        add_test_pcap(self.user)

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/pcaps/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.pcaps_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/pcaps/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.pcaps_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testPcapsList(self):
        self.req = self.factory.get('/pcaps/list/')
        self.req.user = self.user
        response = views.pcaps_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testPcapsjtList(self):
        self.req = self.factory.post('/pcaps/list/jtlist/',
                                     {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.pcaps_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
