import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# El Manager es obligatorio para manejar la creación de usuarios con Custom Models
class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('El usuario debe tener un correo electrónico')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        
        if password:
            user.set_password(password)
        else:
            # Esto hace que el usuario no pueda loguearse con contraseña
            # Útil para usuarios de Google/Facebook
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        # Para el superusuario, forzamos que haya un password
        if not password:
            raise ValueError('El superusuario debe tener una contraseña obligatoriamente')
            
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, username, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=40, unique=True)
    
    # Datos de perfil
    default_post_format = models.CharField(
        max_length=10, 
        choices=[('html', 'html'), ('markdown', 'markdown'), ('raw', 'raw')],
        default='html'
    )
    following_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    
    # Identificador único para API/Headers
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)

    # Estados obligatorios para Django
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False) 
    # is_superuser ya lo incluye PermissionsMixin, no hace falta declararlo aquí

    # Configuración de autenticación
    objects = UserManager() # Enlaza el Manager que creamos arriba

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email