from django.db import models
from django.contrib.auth.models import User

class Author(models.Model):
    #TODO: this is where we will put friends and stuff
    number = models.IntegerField() #TODO: delete this
    friends = models.ManyToManyField('self', related_name='followers',
                                     symmetrical=False)
    user = models.OneToOneField(User,
                                on_delete=models.CASCADE,
                                related_name='author')

    def follow(self, other):
        self.friends.add(other)

    def unfollow(self, other):
        self.friends.remove(other)

    def follows(self, other):
        try:
            self.friends.get(id=other.id)
            return True
        except Author.DoesNotExist:
            return False


    def public_posts(self):
        pass

    def posts_for(self, user):
        pass

    @classmethod
    def from_user(cls, user):
        """
        returns a user's author, or None if it does not have one or
        isn't authenticated.
        """
        if not user.is_authenticated:
            return None

        try:
            return user.author
        except cls.DoesNotExist:
            return None

    class UserNameTaken(Exception):
        pass

    class PasswordsDontMatch(Exception):
        pass

    @classmethod
    def signup(cls, username, password1, password2):
        try:
            User.objects.get(username=username)
            raise cls.UserNameTaken()
        except User.DoesNotExist:
            pass

        if password1 != password2:
            raise cls.PasswordsDontMatch()

        user = User.objects.create_user(username=username,
                                        password=password1)

        return cls.objects.create(number=60, user=user)
