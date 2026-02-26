from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse

class ErrorEmailTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('ui-index') + "api/process-reel/"

    @patch('core.views.download_reel')
    @patch('core.views.send_error_email')
    def test_error_email_sent_on_failure(self, mock_send_email, mock_download):
        # Simulate a failure in download_reel
        mock_download.side_effect = Exception("Simulated Download Failure")
        
        response = self.client.post(self.url, {'url': 'https://www.instagram.com/reel/test/'})
        
        # Verify response is 500
        self.assertEqual(response.status_code, 500)
        
        # Verify send_error_email was called
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        self.assertEqual(kwargs['url'], 'https://www.instagram.com/reel/test/')
        self.assertIn("Simulated Download Failure", kwargs['error_message'])
