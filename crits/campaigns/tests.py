from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.campaigns.views as views
import crits.campaigns.handlers as handlers
from crits.campaigns.campaign import Campaign
from crits.config.config import CRITsConfig
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.core.source_access import SourceAccess

TSRC = "TestSource"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"

CAMPAIGN_NAME = "Test Campaign"
CAMPAIGN_DESCRIPTION = "Test Campaign Description"


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
    Campaign.objects(name=CAMPAIGN_NAME).delete()
    CRITsConfig.drop_collection()


def add_test_campaign(user):
    return handlers.add_campaign(CAMPAIGN_NAME, CAMPAIGN_DESCRIPTION, '',
                                 user.username)


class CampaignHandlerTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()

    def tearDown(self):
        clean_db()

    def testCampaignAdd(self):
        result = add_test_campaign(self.user)
        self.assertTrue(result['success'])
        self.assertEqual(Campaign.objects(name=CAMPAIGN_NAME).count(), 1)

    def testCampaignGet(self):
        add_test_campaign(self.user)
        campaign = Campaign.objects(name=CAMPAIGN_NAME).first()
        self.assertEqual(campaign.name, CAMPAIGN_NAME)


class CampaignViewTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        add_test_campaign(self.user)

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/campaigns/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.campaigns_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/campaigns/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.campaigns_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testCampaignsList(self):
        self.req = self.factory.get('/campaigns/list/')
        self.req.user = self.user
        response = views.campaigns_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testCampaignsjtList(self):
        self.req = self.factory.post('/campaigns/list/jtlist/', {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.campaigns_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
