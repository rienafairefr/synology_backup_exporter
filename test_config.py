import json

from init import get_config


def test_get_config_with_env(monkeypatch, tmpdir):
    monkeypatch.setenv('DSMADDRESS', 'DSM_ADDRESS')
    monkeypatch.setenv('CERT_VERIFY', 'true')
    monkeypatch.setenv('DSM_VERSION', '7')
    config_path = tmpdir / 'config.json'
    config_holes = {'DSMPort': '5000', 'Username': 'admin', 'Password': 'changeme', 'Secure': False, 'ActiveBackup': True, 'HyperBackup': True, 'HyperBackupVault': True, 'ExporterPort': '9771', 'ExporterAddress': '0.0.0.0'}
    expected = {'DSMPort': '5000', 'Username': 'admin', 'Password': 'changeme', 'Secure': False, 'ActiveBackup': True, 'HyperBackup': True, 'HyperBackupVault': True, 'ExporterPort': '9771', 'DSM_Version': 7, 'ExporterAddress': '0.0.0.0', 'DSMAddress': 'DSM_ADDRESS', 'Cert_Verify': True}
    with open(config_path, 'w') as config_file:
        json.dump(config_holes, config_file)
    config, _ = get_config(config_path)
    assert config['DSMAddress'] == 'DSM_ADDRESS'
    assert expected == config


def test_get_config():
    expected = {'DSMAddress': 'syno.ip.add.ress', 'DSMPort': '5000', 'Username': 'admin', 'Password': 'changeme', 'Secure': False, 'Cert_Verify': False, 'ActiveBackup': True, 'HyperBackup': True, 'HyperBackupVault': True, 'ExporterPort': '9771', 'DSM_Version': 7, 'ExporterAddress': '0.0.0.0'}
    config, _ = get_config("config.json.dist")
    assert expected == config
