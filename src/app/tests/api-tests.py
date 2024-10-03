from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from app.models import Reader, TagEvent, Command, APIKey
from django.contrib.auth.models import User
import json

class APITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.api_key = APIKey.objects.create(user=self.user)
        self.client.credentials(HTTP_X_API_KEY=self.api_key.key)

        self.reader = Reader.objects.create(
            serial_number='TEST001',
            ip_address='192.168.1.1',
            location='Test Location'
        )

        self.tag_event = TagEvent.objects.create(
            reader=self.reader,
            epc='123456789',
            first_seen_timestamp='2023-01-01T00:00:00Z',
            antenna_port=1,
            antenna_zone='Zone1',
            peak_rssi=-50.0
        )

    def test_reader_list(self):
        url = reverse('api-reader-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['serial_number'], 'TEST001')

    def test_reader_detail(self):
        url = reverse('api-reader-detail', kwargs={'serial_number': 'TEST001'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['serial_number'], 'TEST001')

    def test_tag_event_list(self):
        url = reverse('api-tag-event-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['epc'], '123456789')

    def test_command_create(self):
        url = reverse('api-command-create')
        data = {
            'reader_serial_number': 'TEST001',
            'command_type': 'start',
            'details': json.dumps({'key': 'value'})
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Command.objects.count(), 1)
        self.assertEqual(Command.objects.first().command_type, 'start')

    def test_invalid_api_key(self):
        self.client.credentials(HTTP_X_API_KEY='invalid_key')
        url = reverse('api-reader-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_missing_api_key(self):
        self.client.credentials()
        url = reverse('api-reader-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_reader_list_filter(self):
        url = reverse('api-reader-list') + '?serial_number=TEST'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

        url = reverse('api-reader-list') + '?serial_number=NONEXISTENT'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

    def test_tag_event_list_filter(self):
        url = reverse('api-tag-event-list') + '?epc=123456789'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

        url = reverse('api-tag-event-list') + '?reader_serial=TEST001'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

        url = reverse('api-tag-event-list') + '?epc=NONEXISTENT'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
