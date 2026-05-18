from django.shortcuts import render

# Create your views here.
"""from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class DashboardView(APIView):
    
    #Endpoint que orquesta el timeline del usuario.
    #Ruta: /v1/timeline/dashboard
    
    def get(self, request, format=None):
        mock_posts = [
            {
                "objectType": "title",
                "streamGlobalPosition": 1,
                "id": "111",
                "text": "Bienvenido a tu timeline, Jeffer! 👋"
            },
            {
                "objectType": "post",
                "streamGlobalPosition": 2,
                "id": "222",
                "blogName": "AlvaroSinApellidos",
                "blog": {
                    "avatar": [
                        {
                            "width": 512,
                            "height": 512,
                            "url": "http://192.168.0.247:9080/media/post_images/image1.jpg",
                        }
                    ],
                    "canBeFollowed": True,
                    "canShowBages": True,
                    "blogViewUrl": "https://192.168.0.247:9080/blog/AlvaroSinApellidos",
                    "description": [
                        {
                            "type": "text",
                            "text": "Descripción del blog de AlvaroSinApellidos"
                        },
                        {
                            "type": "text",
                            "text": "¡Sigue a AlvaroSinApellidos para descubrir contenido increíble sobre arte, música y más!"
                        }
                    ],
                    "followed": False,
                    "isAdult": False,
                    "blogName": "AlvaroSinApellidos",
                    "username": "AlvaroSinApellidos",
                },
                "timestamp": 1776901086,
                "layout": [],
                "trail": [],
                "canEdit": False,
                "canDelete": False,
                "canReply": True,
                "canShare": True,
                "canLike": True,
                "canRepost": True,
                "tags": [
                    {
                        "name": "art",
                    },
                    {
                        "name": "painting",
                    },
                    {
                        "name": "plants",
                    },
                    {
                        "name": "cozy",
                        "type": "trending",
                        "style":{
                            "iconKey": "search_filter_trending",
                            "colors": [
                                "#FF61CE",
                                "#7C5CFF",
                            ]
                        }
                    },
                    {
                        "name": "illustration",
                    }
                ],
                "content": [
                    {
                        "type": "image",
                        "media": [
                            {
                                "url": "http://192.168.0.247:9080/media/post_images/image1.jpg",
                                "type": "image/jpeg",
                                "width": 800,
                                "height": 600
                            }
                        ]
                    },
                    {                    
                        "type": "text",                    
                        "text": "Este es el texto que acompaña a la primera imagen. ¡Qué paisaje tan increíble!"
                    }
                ],
                "followed": False,
                "liked": False,
                "likeCount": 260,
                "repostCount": 53,
                "commentCount": 17,
                "notesCount": 330,
                "createdAt": "2026-04-22T23:38:06.548426Z",
                "updatedAt": "2026-04-22T23:38:06.548438Z",
                "isNsfw": False,
                "date": "2026-04-22T23:38:06.548426Z",
                "state": "published",

            },
            {
                "objectType": "carousel",
                "streamGlobalPosition": 3,
                "id": "333",
                "elements": [
                    {
                        "id": "334",
                        "objectType": "user_card",
                        "resource": [
                            {
                                "id": "101",
                                "username": "MelonMusk",
                                "avatar": "http://192.168.0.247:8000/media/post_images/image1.jpg",
                                "userViewUrl": "https://example.com/user/101",
                                "canBeFollowed": True,
                                "canShowBages": True,
                                "description": "Descripción del usuario",
                                "followed": False,
                                "isAdult": False,
                                "title": "Título del usuario",
                                "uuid": "uuid-101",
                                "posts": [
                                    {
                                        "id": 8622317103967239,
                                        "blogId": 1,
                                        "username": "Jeffer",
                                        "timestamp": 1776901086,
                                        "layout": [],
                                        "tags": [
                                            "art",
                                            "painting",
                                            "cozy",
                                            "plants",
                                            "illustration"
                                        ],
                                        "content": [
                                            {                                               
                                                "type": "image",                                                
                                                "media": [
                                                    {
                                                        "url": "http://192.168.0.247:8000/media/post_images/image1.jpg",
                                                        "type": "image/jpeg",
                                                        "width": 800,
                                                        "height": 600
                                                    }
                                                ]
                                            },
                                            {                                                
                                                "type": "text",                                                
                                                "text": "Este es el texto que acompaña a la primera imagen. ¡Qué paisaje tan increíble!"
                                            }
                                        ],
                                        "likesCount": 260,
                                        "repostsCount": 53,
                                        "commentsCount": 17,
                                        "notesCount": 330,
                                        "createdAt": "2026-04-22T23:38:06.548426Z",
                                        "updatedAt": "2026-04-22T23:38:06.548438Z"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "id": "335",
                        "objectType": "user_card",
                        "resource": [
                            {
                                "id": "102",
                                "username": "Aldair",
                                "avatar": "http://192.168.0.247:8000/media/post_images/image1.jpg",
                                "userViewUrl": "https://example.com/user/102",
                                "canBeFollowed": True,
                                "canShowBages": True,
                                "description": "Descripción del usuario",
                                "followed": False,
                                "isAdult": False,
                                "title": "Título del usuario",
                                "uuid": "uuid-102",
                                "posts": [
                                    {    
                                        "id": 8622317103967239,
                                        "blogId": 1,
                                        "username": "Jeffer",
                                        "timestamp": 1776901086,
                                        "layout": [],
                                        "tags": [
                                            "art",
                                            "painting",
                                            "cozy",
                                            "plants",
                                            "illustration"
                                        ],
                                        "content": [
                                            {                                                
                                                "type": "image",                                               
                                                "media": [
                                                    {
                                                        "url": "http://192.168.0.247:8000/media/post_images/image1.jpg",
                                                        "type": "image/jpeg",
                                                        "width": 800,
                                                        "height": 600
                                                    }
                                                ]
                                            },
                                            {
                                                "type": "text",
                                                "text": "Este es el texto que acompaña a la primera imagen. ¡Qué paisaje tan increíble!"
                                            }
                                        ],
                                        "likesCount": 260,
                                        "repostsCount": 53,
                                        "commentsCount": 17,
                                        "notesCount": 330,
                                        "createdAt": "2026-04-22T23:38:06.548426Z",
                                        "updatedAt": "2026-04-22T23:38:06.548438Z"
                                    }
                                ]
                            }
                        ]
                    }
                ]
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

##EXPLORE SCREEN

class ExploreView(APIView):
    
    #Endpoint que orquesta el timeline del usuario.
    #Ruta: /v1/explore
    
    def get(self, request, format=None):
        mock_posts = [ 
            {
                "objectType": "title",
                "id": "110",
                "streamGlobalPosition": 1,
                "text": "Temas del momento"
            },
            {
                "objectType": "trend",
                "streamGlobalPosition": 2,
                "id": "111",
                "category": "Musíca",
                "count": "300 M de posts",
                "iconUrl": "http://192.168.0.247:9080/media/post_images/image1.jpg",
                "subType": "tag",
                "elements": [
                    {
                        "id": "111",
                        "objectType": "tag",
                        "name": "rock",
                        "isFollowed": False,
                        "resource": [
                            {
                                "id": 111,
                                "blogId": 111,
                                "username": "user_111",
                                "timestamp": 1776901086,
                                "layout": [],
                                "tags": [
                                    "art",
                                    "painting",
                                    "cozy",
                                    "plants",
                                    "illustration"
                                ],
                                "content": [
                                    {
                                        "id": 1,
                                        "type": "image",
                                        "order": 0,
                                        "media": [
                                            {
                                                "url": "http://192.168.0.247:9080/media/post_images/image1.jpg",
                                                "type": "image/jpeg",
                                                "width": 800,
                                                "height": 600
                                            }
                                        ]
                                    },
                                    {
                                        "id": 2,
                                        "type": "text",
                                        "order": 1,
                                        "text": "Este es el texto que acompaña a la primera imagen. ¡Qué paisaje tan increíble!"
                                    },
                                        {
                                        "id": 3,
                                        "type": "video",
                                        "order": 0,
                                        "media": [
                                            {
                                                "url": "http://localhost:9080/media/post_videos/video1.mp4",
                                                "type": "video/mp4",
                                                "width": 800,
                                                "height": 600
                                            }
                                        ]
                                    }
                                ],
                                "likesCount": 260,
                                "repostsCount": 53,
                                "commentsCount": 17,
                                "notesCount": 330,
                                "createdAt": "2026-04-22T23:38:06.548426Z",
                                "updatedAt": "2026-04-22T23:38:06.548438Z"
                            }
                        ]
                    }
                ]
            },
            {
                "objectType": "trend",
                "id": "555",
                "streamGlobalPosition": 3,
                "category": "Music",
                "count": "300 M de posts",
                "iconUrl": "https://cdn-icons-png.flaticon.com/512/727/727245.png",
                "subType": "video",
                "elements": [
                    {
                        "id": "222",
                        "objectType": "video",
                        "resource": [
                            {
                                "id": 777,
                                "blogId": 777,
                                "username": "user_777",
                                "timestamp": 1776901086,
                                "layout": [],
                                "tags": [
                                    "art",
                                    "painting",
                                    "cozy",
                                    "plants",
                                    "illustration"
                                ],
                                "content": [
                                    {
                                        "id": 777,
                                        "type": "video",
                                        "order": 0,
                                        "media": [
                                            {
                                                "url": "http://192.168.0.247:9080/media/post_videos/video1.mp4",
                                                "type": "video/mp4",
                                                "width": 480,
                                                "height": 840
                                            }
                                        ]
                                    }
                                ],
                                "likesCount": 260,
                                "repostsCount": 53,
                                "commentsCount": 17,
                                "notesCount": 330,
                                "createdAt": "2026-04-22T23:38:06.548426Z",
                                "updatedAt": "2026-04-22T23:38:06.548438Z"
                            }
                        ]
                    }
                ]
            }
        ]

        response_data = {
            "meta": {
                "status": 200,
                "msg": "OK",
                "xLoomUserId": str(request.user.id) if request.user.is_authenticated else "anonymous"
            },
            "response": {
                "explore": {
                    "elements": mock_posts,
                    "cursor": "2"
                }
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)"""