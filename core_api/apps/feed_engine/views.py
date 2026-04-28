from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class DashboardView(APIView):
    """
    Endpoint que orquesta el timeline del usuario.
    Ruta: /v1/timeline/dashboard
    """
    def get(self, request, format=None):
        mock_posts = [ 
             {
                "objectType": "title",
                "id": "e2eLe8787g",
                "streamGlobalPosition": 4,
                "text": "Más Usuarios! 🚀"
            }
    ]

        response_data = {
            "meta": {
                "status": 200,
                "msg": "OK",
                "xLoomUserId": str(request.user.id) if request.user.is_authenticated else "anonymous"
            },
            "response": {
                "timeline": {
                    "elements": mock_posts,
                    "cursor": "2"
                }
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)