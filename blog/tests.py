from django.test import TestCase
from .models import Post, Privacy
from users.models import Author
import datetime

# Create your tests here.
class PrivacyTestCase(TestCase):
    def setUp(self):
        self.author_A = Author.signup("a", "pw", "pw")
        self.author_B = Author.signup("b", "pw", "pw")
        self.author_C = Author.signup("c", "pw", "pw")

        self.author_A.follow(self.author_B)
        self.author_B.follow(self.author_A)

        self.author_C.follow(self.author_A)

    def test_private(self):
        post = Post.objects.create(date=datetime.date.today(),
                                   title="a",
                                   content="a",
                                   author=self.author_A,
                                   privacy=Privacy.PRIVATE)

        self.assertTrue(post.viewable_by(self.author_A.user))
        self.assertFalse(post.viewable_by(self.author_B.user))
        self.assertFalse(post.viewable_by(self.author_C.user))

    def test_url_only(self):
        post = Post.objects.create(date=datetime.date.today(),
                                   title="a",
                                   content="a",
                                   author=self.author_A,
                                   privacy=Privacy.URL_ONLY)

        self.assertTrue(post.viewable_by(self.author_A.user))
        self.assertTrue(post.viewable_by(self.author_B.user))
        self.assertTrue(post.viewable_by(self.author_C.user))

    def test_friends(self):
        post = Post.objects.create(date=datetime.date.today(),
                                   title="a",
                                   content="a",
                                   author=self.author_A,
                                   privacy=Privacy.FRIENDS)

        self.assertTrue(post.viewable_by(self.author_A.user))
        self.assertTrue(post.viewable_by(self.author_B.user))
        self.assertFalse(post.viewable_by(self.author_C.user))

    def test_foaf(self):
        #TODO
        pass

    def test_public(self):
        post = Post.objects.create(date=datetime.date.today(),
                                   title="a",
                                   content="a",
                                   author=self.author_A,
                                   privacy=Privacy.PUBLIC)

        self.assertTrue(post.viewable_by(self.author_A.user))
        self.assertTrue(post.viewable_by(self.author_B.user))
        self.assertTrue(post.viewable_by(self.author_C.user))
