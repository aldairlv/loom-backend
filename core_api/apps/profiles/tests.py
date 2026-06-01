from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Profile


class ProfileSignalsTest(TestCase):
    def test_profile_is_created_when_user_is_created(self):
        User = get_user_model()
        user = User.objects.create_user(
            email='user@example.com',
            username='testuser',
            password='secret123',
        )

        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, Profile)
        self.assertEqual(user.profile.display_name, 'testuser')
