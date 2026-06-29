from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.actors.views as views
import crits.actors.handlers as handlers
from crits.actors.actor import Actor
from crits.config.config import CRITsConfig
from crits.core.user import CRITsUser
from crits.core.handlers import add_new_source
from crits.core.management.commands.create_roles import add_uber_admin_role
from crits.core.source_access import SourceAccess

TSRC = "TestSource"
TUSER_NAME = "test_user"
TUSER_PASS = "!@#j54kfeimn?>S<D"
TUSER_EMAIL = "test_user@example.com"

ACTOR_NAME = "Test Actor"


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
    Actor.objects(name=ACTOR_NAME).delete()
    CRITsConfig.drop_collection()


def add_test_actor(user):
    return handlers.add_new_actor(ACTOR_NAME, source=TSRC, source_tlp='red',
                                  user=user)


class ActorHandlerTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()

    def tearDown(self):
        clean_db()

    def testActorAdd(self):
        result = add_test_actor(self.user)
        self.assertTrue(result['success'])
        self.assertEqual(Actor.objects(name=ACTOR_NAME).count(), 1)

    def testActorGet(self):
        add_test_actor(self.user)
        actor = Actor.objects(name=ACTOR_NAME).first()
        self.assertEqual(actor.name, ACTOR_NAME)


class ActorViewTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        add_test_actor(self.user)

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/actors/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.actors_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/actors/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.actors_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testActorsList(self):
        self.req = self.factory.get('/actors/list/')
        self.req.user = self.user
        response = views.actors_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testActorsjtList(self):
        self.req = self.factory.post('/actors/list/jtlist/', {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.actors_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
