from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower

class UserManager(BaseUserManager):
    use_in_migrations = True
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('E-posta gereklidir.')
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra)

class User(AbstractUser):
    privacy_accepted_at = models.DateTimeField(null=True,blank=True,editable=False)
    privacy_version = models.CharField(max_length=30,blank=True,default='',editable=False)
    username = None
    email = models.EmailField(unique=True)
    must_change_password = models.BooleanField(default=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()
    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), name='unique_email_case_insensitive')]
