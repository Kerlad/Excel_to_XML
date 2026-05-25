import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import requests
from unittest.mock import patch, MagicMock

# Avoid pytest collecting the imported function as a test
network_client_mod = __import__('network.client', fromlist=['test_external_access', 'get_network_diagnostics', 'NetworkStatus'])
_check_network = network_client_mod.test_external_access
get_network_diagnostics = network_client_mod.get_network_diagnostics
NetworkStatus = network_client_mod.NetworkStatus


class TestNetworkClient:
    def test_requests_unavailable(self):
        with patch('network.client.REQUESTS_AVAILABLE', False):
            status, msg = _check_network()
            assert status == NetworkStatus.UNKNOWN_ERROR
            assert 'requests' in msg

    def test_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('network.client.REQUESTS_AVAILABLE', True), \
             patch('network.client.requests.get', return_value=mock_response):
            status, msg = _check_network()
            assert status == NetworkStatus.SUCCESS
            assert '200' in msg

    def test_http_403(self):
        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch('network.client.REQUESTS_AVAILABLE', True), \
             patch('network.client.requests.get', return_value=mock_response):
            status, msg = _check_network()
            assert status == NetworkStatus.SUCCESS
            assert '403' in msg

    def test_http_500(self):
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('network.client.REQUESTS_AVAILABLE', True), \
             patch('network.client.requests.get', return_value=mock_response):
            status, msg = _check_network()
            assert status == NetworkStatus.NETWORK_ERROR
            assert '500' in msg

    def test_timeout(self):
        with patch('network.client.REQUESTS_AVAILABLE', True), \
             patch('network.client.requests.get',
                   side_effect=requests.exceptions.Timeout("Timeout")):
            status, msg = _check_network()
            assert status == NetworkStatus.TIMEOUT

    def test_connection_error(self):
        with patch('network.client.REQUESTS_AVAILABLE', True), \
             patch('network.client.requests.get',
                   side_effect=requests.exceptions.ConnectionError("Connection refused")):
            status, msg = _check_network()
            assert status == NetworkStatus.NETWORK_ERROR

    def test_unknown_error(self):
        with patch('network.client.REQUESTS_AVAILABLE', True), \
             patch('network.client.requests.get',
                   side_effect=requests.exceptions.RequestException("Something weird")):
            status, msg = _check_network()
            assert status == NetworkStatus.UNKNOWN_ERROR

    def test_get_network_diagnostics(self):
        diag = get_network_diagnostics()
        assert 'negotiate_available' in diag
        assert 'detected_proxy' in diag
        assert 'auth_method' in diag
        assert 'tls_ok' in diag
        assert 'proxy_auth_ok' in diag
        assert 'recommendation' in diag
        assert isinstance(diag['negotiate_available'], bool)
