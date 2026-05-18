from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .serializers import EmailValidationRequestSerializer, EmailValidationResponseSerializer, NetworkMetaSerializer, NetworkValidateEmailDataSerializer
from drf_spectacular.utils import extend_schema

UserModel = get_user_model()

class EmailValidationView(APIView):
    permission_classes = [] # No authentication required for this endpoint
    authentication_classes = [] # No authentication required for this endpoint

    @extend_schema(
        request=EmailValidationRequestSerializer,
        responses=EmailValidationResponseSerializer
    )
    def post(self, request, *args, **kwargs):
        serializer = EmailValidationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user_exists = UserModel.objects.filter(email=email).exists()

        if user_exists:
            response_data = {
                "meta": {"status": 409, "msg": "Conflict"}, # 409 Conflict for existing resource
                "response": {"available": False, "message": "Este usuario ya existe!"}
            }
            status_code = status.HTTP_200_OK
        else:
            response_data = {
                "meta": {"status": 200, "msg": "OK"},
                "response": {"available": True, "message": "Email disponible."}
            }
            status_code = status.HTTP_200_OK
        
        # Use the response serializer for consistency and validation
        response_serializer = EmailValidationResponseSerializer(response_data)
        return Response(response_serializer.data, status=status_code)
