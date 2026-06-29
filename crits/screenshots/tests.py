import io

from PIL import Image

from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.screenshots.views as views
import crits.screenshots.handlers as handlers
from crits.screenshots.screenshot import Screenshot
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

SAMPLE_MD5 = "a" * 32
SAMPLE_FILENAME = "host_sample.bin"


def make_png():
    """
    Build an in-memory PNG file handle to use as a screenshot.
    """

    buf = io.BytesIO()
    Image.new('RGB', (32, 32), 'blue').save(buf, 'PNG')
    buf.seek(0)
    buf.name = 'shot.png'
    return buf


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
    Screenshot.drop_collection()
    CRITsConfig.drop_collection()


def make_sample():
    """
    Create a Sample to attach screenshots to.
    """

    sample = Sample()
    sample.md5 = SAMPLE_MD5
    sample.filename = SAMPLE_FILENAME
    sample.add_source(source=TSRC, analyst=TUSER_NAME, tlp='red')
    sample.save(username=TUSER_NAME)
    return sample


def add_test_screenshot(user, sample):
    return handlers.add_screenshot('test screenshot', '', TSRC, '', '', 'red',
                                   user.username, make_png(), None,
                                   str(sample.id), 'Sample')


class ScreenshotHandlerTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        self.sample = make_sample()

    def tearDown(self):
        clean_db()

    def testScreenshotAdd(self):
        result = add_test_screenshot(self.user, self.sample)
        self.assertTrue(result['success'])
        self.assertEqual(Screenshot.objects.count(), 1)

    def testScreenshotThumbnail(self):
        # Exercises generate_thumbnail(), which broke on Pillow >= 10.
        add_test_screenshot(self.user, self.sample)
        shot = Screenshot.objects.first()
        self.assertTrue(shot.thumb)
        self.assertEqual(shot.width, 32)


class ScreenshotViewTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        self.sample = make_sample()
        add_test_screenshot(self.user, self.sample)

    def tearDown(self):
        clean_db()

    def testUserInactiveRedirect(self):
        self.req = self.factory.get('/screenshots/list/')
        self.req.user = self.user
        self.req.user.mark_inactive()
        response = views.screenshots_listing(self.req)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/login/?next=/screenshots/list/" in response['Location'])
        self.req.user.mark_active()
        response = views.screenshots_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testScreenshotsList(self):
        self.req = self.factory.get('/screenshots/list/')
        self.req.user = self.user
        response = views.screenshots_listing(self.req)
        self.assertEqual(response.status_code, 200)

    def testScreenshotsjtList(self):
        self.req = self.factory.post('/screenshots/list/jtlist/', {},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.req.user = self.user
        response = views.screenshots_listing(self.req, 'jtlist')
        self.assertEqual(response.status_code, 200)
