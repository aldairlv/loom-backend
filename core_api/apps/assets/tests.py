from django.test import TestCase

from .serializers import generate_unique_filename


class MediaSerializerTests(TestCase):
    def test_generate_unique_filename_uses_content_type_extension_when_filename_has_no_extension(self):
        filename = 'blob'
        result = generate_unique_filename(filename, 'video/mp4')

        self.assertTrue(result.endswith('.mp4'))
        self.assertEqual(result.count('.'), 1)

    def test_generate_unique_filename_preserves_existing_extension(self):
        filename = 'my_video.mp4'
        result = generate_unique_filename(filename, 'video/mp4')

        self.assertTrue(result.endswith('.mp4'))
        self.assertEqual(result.count('.'), 1)
