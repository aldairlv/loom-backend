# apps/accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from dj_rest_auth.registration.serializers import RegisterSerializer as RestAuthRegisterSerializer

# Get the custom User model
UserModel = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        # Añade 'date_joined' aquí:
        fields = ['id', 'email', 'username', 'password', 'date_joined', 'birth_date'] 
        extra_kwargs = {
            'password': {'write_only': True}
        }

class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login. Does not inherit from dj_rest_auth's LoginSerializer
    to avoid circular imports. dj_rest_auth will still use its backend logic.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        style={'input_type': 'password'}, 
        trim_whitespace=False, 
        required=True
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Usamos el backend de autenticación de Django.
            # Gracias a nuestra configuración, esto usará allauth para validar por email.
            user = authenticate(
                request=self.context.get('request'),
                email=email, 
                password=password
            )

            # Si authenticate() falla, devuelve None.
            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Must include "email" and "password".'
            raise serializers.ValidationError(msg, code='authorization')

        # Si la autenticación es exitosa, añadimos el usuario a los datos validados.
        attrs['user'] = user
        return attrs

# New RegisterSerializer
class RegisterSerializer(RestAuthRegisterSerializer):
    birth_date = serializers.DateField(required=False, allow_null=True) # Add birth_date

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data['birth_date'] = self.validated_data.get('birth_date', None)
        return data

    def save(self, request):
        user = super().save(request)
        user.birth_date = self.cleaned_data.get('birth_date')
        user.save()
        return user

# New serializers for email validation endpoint
class EmailValidationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class NetworkMetaSerializer(serializers.Serializer):
    status = serializers.IntegerField()
    msg = serializers.CharField()

class NetworkValidateEmailDataSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    message = serializers.CharField(allow_null=True, required=False)

class EmailValidationResponseSerializer(serializers.Serializer):
    meta = NetworkMetaSerializer()
    response = NetworkValidateEmailDataSerializer()