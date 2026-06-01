from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from profiles.models import Profile
from posts.models import Post
from relationships.models import Follow


class FeedViewSetTests(APITestCase):
    """
    Tests for the FeedViewSet, which provides the main content feed for a user.
    """

    def setUp(self):
        """Set up users, profiles, and relationships for testing."""
        # User 1 (The one making the requests)
        self.user1 = User.objects.create_user(username='user1', email='user1@test.com', password='password123')
        self.profile1 = Profile.objects.get(user=self.user1)

        # User 2 (A profile that user1 follows)
        self.user2 = User.objects.create_user(username='user2', email='user2@test.com', password='password123')
        self.profile2 = Profile.objects.get(user=self.user2)

        # User 3 (A profile that user1 does NOT follow)
        self.user3 = User.objects.create_user(username='user3', email='user3@test.com', password='password123')
        self.profile3 = Profile.objects.get(user=self.user3)

        # User1 follows User2
        Follow.objects.create(from_profile=self.profile1, to_profile=self.profile2)

        # Create posts from different users at different times
        self.post_from_followed = Post.objects.create(
            author=self.profile2,
            created_at=timezone.now() - timedelta(hours=1)
        )
        self.post_from_unfollowed = Post.objects.create(
            author=self.profile3,
            created_at=timezone.now() - timedelta(hours=2)
        )
        self.own_post = Post.objects.create(
            author=self.profile1,
            created_at=timezone.now() - timedelta(hours=3)
        )
        self.newest_post_from_followed = Post.objects.create(
            author=self.profile2,
            created_at=timezone.now()
        )

        self.feed_url = reverse('feeds-list')
        self.client.force_authenticate(user=self.user1)

    def test_feed_requires_authentication(self):
        """
        Verify that unauthenticated users cannot access the feed.
        """
        self.client.logout()
        response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_feed_contains_posts_from_followed_profiles(self):
        """
        Verify that the feed includes posts from profiles the user follows.
        """
        response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']
        post_ids = [post['id'] for post in results]

        self.assertIn(str(self.post_from_followed.id), post_ids)
        self.assertIn(str(self.newest_post_from_followed.id), post_ids)

    def test_feed_does_not_contain_posts_from_unfollowed_profiles(self):
        """
        Verify that the feed does not include posts from profiles the user does not follow.
        """
        response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']
        post_ids = [post['id'] for post in results]

        self.assertNotIn(str(self.post_from_unfollowed.id), post_ids)

    def test_feed_does_not_contain_own_posts(self):
        """
        Verify that the user's own posts are not included in their feed.
        """
        response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']
        post_ids = [post['id'] for post in results]

        self.assertNotIn(str(self.own_post.id), post_ids)

    def test_feed_is_ordered_by_creation_date_descending(self):
        """
        Verify that posts in the feed are sorted from newest to oldest.
        """
        response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']
        self.assertEqual(len(results), 2)

        # The first post in the list should be the newest one
        self.assertEqual(results[0]['id'], str(self.newest_post_from_followed.id))
        self.assertEqual(results[1]['id'], str(self.post_from_followed.id))

    # Note: A test for pagination would require knowing the specific implementation
    # (e.g., CursorPagination). If you provide the FeedViewSet code, I can add
    # a specific test for it.