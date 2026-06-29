from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.indicators.views as views
import crits.indicators.handlers as handlers
from crits.indicators.indicator import Indicator
from crits.config.config import CRITsConfig
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.core.source_access import SourceAccess
from crits.domains.domain import TLD
from crits.vocabulary.indicators import (IndicatorTypes,
                                         IndicatorThreatTypes,
                                         IndicatorAttackTypes)

TSRC = "TestSource"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"

IND_VALUE = "indicator.example.com"
IND_TYPE = IndicatorTypes.DOMAIN


def prep_db():
    """
    Prep the DB for the test.
    """

    clean_db()
    # A CRITsConfig is expected to exist at runtime; create one for the tests.
    CRITsConfig().save()
    # Domain indicators validate their TLD against the TLD collection, which
    # the unit-test DB doesn't populate; seed the one we need.
    TLD.objects(tld='com').update_one(set__tld='com', upsert=True)
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
    Indicator.objects(value=IND_VALUE).delete()
    TLD.objects(tld='com').delete()
    CRITsConfig.drop_collection()


def add_test_indicator(user):
    """
    Add a single indicator as the test user.
    """

    return handlers.handle_indicator_ind(
        IND_VALUE,
        TSRC,
        IND_TYPE,
        IndicatorThreatTypes.UNKNOWN,
        IndicatorAttackTypes.UNKNOWN,
        user,
        source_tlp='red',
    )


class IndicatorHandlerTests(SimpleTestCase):
    """
    Test Indicator handlers.
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

    def testIndicatorAdd(self):
        result = add_test_indicator(self.user)
        self.assertTrue(result['success'])
        self.assertEqual(Indicator.objects(value=IND_VALUE).count(), 1)

    def testIndicatorGet(self):
        add_test_indicator(self.user)
        ind = Indicator.objects(value=IND_VALUE).first()
        self.assertEqual(ind.value, IND_VALUE)
        self.assertEqual(ind.ind_type, IND_TYPE)

    def testCSVImport(self):
        # The CSV/text importer ran csv.DictReader over BytesIO, which raises
        # in Py3 ("iterator should return strings, not bytes").
        csv_blob = ("Indicator,Type,Threat Type,Attack Type\n"
                    "csv-indicator.example.com,Domain,Unknown,Unknown\n")
        result = handlers.handle_indicator_csv(csv_blob, 'ti', self.user, TSRC,
                                               source_tlp='red', add_domain=True)
        self.assertTrue(result['success'])
        self.assertEqual(
            Indicator.objects(value='csv-indicator.example.com').count(), 1)
        Indicator.objects(value='csv-indicator.example.com').delete()


class IndicatorViewTests(SimpleTestCase):
    """
    Test Indicator views.
    """

    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        add_test_indicator(self.user)

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/indicators/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.indicators_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/indicators/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.indicators_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testIndicatorsList(self):
        self.req = self.factory.get('/indicators/list/')
        self.req.user = self.user
        response = views.indicators_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testIndicatorsjtList(self):
        self.req = self.factory.post('/indicators/list/jtlist/',
                                     {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.indicators_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
