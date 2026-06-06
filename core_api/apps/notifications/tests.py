from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from profiles.models import Profile
from posts.models import Post
from interactions.models import Like
from notifications.models import Notification


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1', email='user1@test.com', password='password123'
        )
        self.profile1 = Profile.objects.get(user=self.user1)

        self.user2 = User.objects.create_user(
            username='user2', email='user2@test.com', password='password123'
        )
        self.profile2 = Profile.objects.get(user=self.user2)

        self.post = Post.objects.create(author=self.profile1)
        self.like = Like.objects.create(profile=self.profile2, post=self.post)

        self.notification = Notification.objects.create(
            recipient=self.profile1,
            event_type=Notification.EventType.LIKE,
            content_type=ContentType.objects.get_for_model(Like),
            object_id=self.like.id,
        )

        self.unrelated_notification = Notification.objects.create(
            recipient=self.profile2,
            event_type=Notification.EventType.LIKE,
            content_type=ContentType.objects.get_for_model(Like),
            object_id=self.like.id,
        )

        self.url = reverse('notification-list')
        self.client.force_authenticate(user=self.user1)

    def test_notifications_list_requires_authentication(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_notifications_list_returns_only_recipient_notifications(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # New response shape mirrors feed serializer structure
        meta = response.data.get('meta')
        self.assertIsNotNone(meta)
        self.assertEqual(meta.get('status'), 200)

        notifications_block = response.data.get('response', {}).get('notifications', {})
        elements = notifications_block.get('elements', [])
        self.assertEqual(len(elements), 1)
        item = elements[0]
        self.assertEqual(item['id'], str(self.notification.id))
        self.assertEqual(item['content_type'], 'like')
        self.assertEqual(item['event_type'], Notification.EventType.LIKE)
        self.assertEqual(item['target_data']['id'], str(self.like.id))
        self.assertEqual(item['target_data']['author']['id'], str(self.like.profile_id))
        self.assertEqual(item['target_data']['author']['display_name'], self.like.profile.display_name)
        self.assertEqual(item['target_data']['post']['id'], str(self.post.id))
        self.assertEqual(item['target_data']['post']['content_data'], [])
        # cursor must be present (may be None)
        self.assertIn('queryParams', notifications_block)

    def test_notifications_list_does_not_return_other_user_notifications(self):
        response = self.client.get(self.url)
        notifications_block = response.data.get('response', {}).get('notifications', {})
        elements = notifications_block.get('elements', [])
        ids = [item['id'] for item in elements]
        self.assertNotIn(str(self.unrelated_notification.id), ids)
