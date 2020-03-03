from django.db import models
from users.models import Author

class Privacy:
    #TODO: private to specific author
    PRIVATE  = 0
    URL_ONLY = 1
    FRIENDS  = 2
    FOAF     = 3
    PUBLIC   = 4

# Create your models here.
class Post(models.Model):
    date = models.DateField()
    title = models.CharField(max_length=150)
    content = models.CharField(max_length=8192)
    markdown = models.BooleanField(default=False)
    author = models.ForeignKey(Author, on_delete=models.CASCADE,
                               related_name='posts')
    privacy = models.IntegerField(default=Privacy.PUBLIC)

    def viewable_by(self, user):
        if (self.privacy == Privacy.PUBLIC or
            self.privacy == Privacy.URL_ONLY):
            return True

        viewer = Author.from_user(user)

        if viewer is None:
            return False

        if self.privacy == Privacy.PRIVATE:
            return self.author == viewer
        elif self.privacy == Privacy.FRIENDS:
            return self.author.friends_with(viewer)
        elif self.privacy == Privacy.FOAF:
            #TODO
            return False

        return False
