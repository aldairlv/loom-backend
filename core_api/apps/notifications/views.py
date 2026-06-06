from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, UserDevice
from .serializers import NotificationSerializer, UserDeviceSerializer


class NotificationsCursorPagination(CursorPagination):
    page_size = 20
    ordering = '-created_at'


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationsCursorPagination

    def get_queryset(self):
        profile = getattr(self.request.user, 'profile', None)
        if profile is None:
            return Notification.objects.none()
        return Notification.objects.filter(recipient=profile).select_related('content_type')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            elements = []
            for item in serializer.data:
                # ensure id is string and attach a type discriminator
                item['id'] = str(item.get('id'))
                item['objectType'] = 'notification'
                elements.append(item)

            # try to obtain next cursor from paginator's next link
            cursor = request.query_params.get(self.pagination_class.cursor_query_param)
            next_link = self.paginator.get_next_link() if hasattr(self, 'paginator') else None
            if next_link:
                from urllib.parse import urlparse, parse_qs
                parsed = parse_qs(urlparse(next_link).query)
                next_cursor = parsed.get(self.pagination_class.cursor_query_param)
                if next_cursor:
                    cursor = next_cursor[0]

            user_id = str(request.user.id) if request and request.user.is_authenticated else None

            return Response({
                'meta': {
                    'status': 200,
                    'msg': 'OK',
                    'xRoomUserId': user_id,
                },
                'response': {
                    'notifications': {
                        'elements': elements,
                        'queryParams': {'cursor': cursor}
                    }
                }
            })

        serializer = self.get_serializer(queryset, many=True)
        # Fallback when pagination is not applied
        return Response({
            'meta': {
                'status': 200,
                'msg': 'OK',
                'xRoomUserId': str(request.user.id) if request.user.is_authenticated else None,
            },
            'response': {
                'notifications': {
                    'elements': serializer.data,
                    'queryParams': {'cursor': None}
                }
            }
        })

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request, 'cursor': self.request.query_params.get('cursor')})
        return context


class RegisterDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve todos los dispositivos registrados para el usuario actual.
        """
        devices = UserDevice.objects.filter(account=request.user)
        serializer = UserDeviceSerializer(devices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Registra, actualiza o desactiva un dispositivo para el usuario actual.
        Espera: device_id, registration_token, device_type, is_active
        """
        device_id = request.data.get('device_id')
        registration_token = request.data.get('registration_token')
        device_type = request.data.get('device_type')
        is_active = request.data.get('is_active', True)

        if is_active:
            if not all([device_id, registration_token, device_type]):
                return Response(
                    {"error": "Para activar el dispositivo necesitas device_id, registration_token y device_type"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            device, created = UserDevice.objects.update_or_create(
                device_id=device_id,
                defaults={
                    'account': request.user,
                    'registration_token': registration_token,
                    'device_type': device_type,
                    'is_active': True,
                }
            )
        else:
            if not device_id:
                return Response(
                    {"error": "Para desactivar el dispositivo necesitas device_id"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                device = UserDevice.objects.get(device_id=device_id, account=request.user)
            except UserDevice.DoesNotExist:
                return Response(
                    {"message": "Device not found or already inactive"},
                    status=status.HTTP_200_OK
                )

            device.is_active = False
            if registration_token is not None:
                device.registration_token = registration_token
            if device_type is not None:
                device.device_type = device_type
            device.save()
            created = False

        serializer = UserDeviceSerializer(device)
        message = "Device registrado y activo" if is_active else "Device desactivado con éxito"
        return Response(
            {
                "message": message,
                "device": serializer.data,
                "created": created
            },
            status=status.HTTP_201_CREATED if is_active and created else status.HTTP_200_OK
        )
