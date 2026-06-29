import json

from django.conf import settings
from django.test import SimpleTestCase
from django.test.client import RequestFactory

import crits.comments.handlers as handlers
from crits.comments.comment import Comment
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

SAMPLE_MD5 = "e" * 32
SAMPLE_FILENAME = "comment_host.bin"
COMMENT_TEXT = "This is a test comment"


def prep_db():
    clean_db()
    CRITsConfig().save()
    add_new_source(TSRC, TUSER_NAME)
    add_uber_admin_role(drop=False)
    user = CRITsUser.create_user(username=TUSER_NAME, password=TUSER_PASS,
                                 email=TUSER_EMAIL)
    user.roles = [settings.ADMIN_ROLE]
    user.organization = TSRC
    user.save()


def clean_db():
    src = SourceAccess.objects(name=TSRC).first()
    if src:
        src.delete()
    user = CRITsUser.objects(username=TUSER_NAME).first()
    if user:
        user.delete()
    Sample.objects(md5=SAMPLE_MD5).delete()
    Comment.objects(comment=COMMENT_TEXT).delete()
    CRITsConfig.drop_collection()


def make_sample():
    sample = Sample()
    sample.md5 = SAMPLE_MD5
    sample.filename = SAMPLE_FILENAME
    sample.add_source(source=TSRC, analyst=TUSER_NAME, tlp='red')
    sample.save(username=TUSER_NAME)
    return sample


class CommentHandlerTests(SimpleTestCase):
    def setUp(self):
        prep_db()
        self.factory = RequestFactory()
        self.user = CRITsUser.objects(username=TUSER_NAME).first()
        self.user.get_access_list(update=True)
        self.user.save()
        self.sample = make_sample()

    def tearDown(self):
        clean_db()

    def testCommentAdd(self):
        cleaned_data = {'comment': COMMENT_TEXT, 'url_key': str(self.sample.id)}
        response = handlers.comment_add(cleaned_data, 'Sample',
                                        str(self.sample.id), '', {}, TUSER_NAME)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        self.assertEqual(Comment.objects(comment=COMMENT_TEXT).count(), 1)
