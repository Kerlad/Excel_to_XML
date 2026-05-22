import sys, os, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from utils.proxy_manager import (
    load_proxy_settings, save_proxy_settings, build_proxies_for_requests
)
from utils.crypto import clear_caches


@pytest.fixture(autouse=True)
def reset_crypto():
    clear_caches()
    yield


class TestProxyManager:
    def test_load_defaults_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = load_proxy_settings(tmpdir)
            assert settings['mode'] == 'off'
            assert settings['tls_verify'] is True
            assert settings['url'] == ''

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            to_save = {
                'mode': 'manual', 'url': 'http://proxy:8080',
                'username': 'user', 'password': 'pass',
                'tls_verify': True
            }
            ok, msg = save_proxy_settings(tmpdir, to_save)
            assert ok
            loaded = load_proxy_settings(tmpdir)
            assert loaded['mode'] == 'manual'
            assert loaded['url'] == 'http://proxy:8080'
            assert loaded['username'] == 'user'
            assert loaded['password'] == 'pass'

    def test_save_missing_url_manual(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ok, msg = save_proxy_settings(tmpdir, {'mode': 'manual', 'url': ''})
            assert not ok

    def test_save_and_load_encrypted_credentials(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            to_save = {
                'mode': 'manual', 'url': 'http://proxy:8080',
                'username': 'testuser', 'password': 'testpass',
                'tls_verify': True
            }
            save_proxy_settings(tmpdir, to_save)
            settings_file = os.path.join(tmpdir, 'proxy_settings.json')
            with open(settings_file, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            assert raw['username'] == ''
            assert raw['password'] == ''
            assert raw['username_encrypted'] != ''
            assert raw['password_encrypted'] != ''

    def test_build_proxies_off(self):
        assert build_proxies_for_requests({'mode': 'off'}) is None

    def test_build_proxies_auto(self):
        proxies = build_proxies_for_requests({'mode': 'auto'})
        assert proxies is None or isinstance(proxies, dict)

    def test_build_proxies_manual_no_auth(self):
        proxies = build_proxies_for_requests({
            'mode': 'manual', 'url': 'http://proxy:8080',
            'username': '', 'password': ''
        })
        assert proxies == {'http': 'http://proxy:8080', 'https': 'http://proxy:8080'}

    def test_build_proxies_manual_with_auth(self):
        proxies = build_proxies_for_requests({
            'mode': 'manual', 'url': 'http://proxy:8080',
            'username': 'user', 'password': 'pass'
        })
        assert proxies is not None
        assert proxies['_username'] == 'user'
        assert proxies['_password'] == 'pass'
        assert 'user' not in proxies['http']
        assert 'pass' not in proxies['http']

    def test_build_proxies_manual_empty_url(self):
        assert build_proxies_for_requests({'mode': 'manual', 'url': ''}) is None

    def test_load_corrupted_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = os.path.join(tmpdir, 'proxy_settings.json')
            with open(settings_file, 'w', encoding='utf-8') as f:
                f.write("not json")
            settings = load_proxy_settings(tmpdir)
            assert settings['mode'] == 'off'

    def test_tls_verify_persisted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            save_proxy_settings(tmpdir, {
                'mode': 'off', 'url': '', 'username': '', 'password': '',
                'tls_verify': False
            })
            loaded = load_proxy_settings(tmpdir)
            assert loaded['tls_verify'] is False
