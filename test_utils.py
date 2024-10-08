import pytest

from init import convert_to_bool, convert_to_int


def test_convert_to_bool():
    assert convert_to_bool("yes")
    assert convert_to_bool("true")
    assert convert_to_bool("True")
    assert not convert_to_bool("false")
    assert not convert_to_bool("False")
    assert not convert_to_bool(None)


def test_convert_to_int():
    assert convert_to_int("1") == 1
    pytest.raises(TypeError, lambda: convert_to_int(None))
    pytest.raises(ValueError, lambda: convert_to_int("TTTT"))


def test_metrics(mocker):
    mocker.patch('init.active_backup_get_info', return_value=["hello"])
    mocker.patch('init.hyper_backup_get_info', return_value=["beautiful"])
    mocker.patch('init.hyper_backup_vault_get_info', return_value=["world"])
    from init import BackupsCollector
    collector = BackupsCollector({'ActiveBackup': False, 'HyperBackup': False, 'HyperBackupVault': False}, None)
    collector.config = {'ActiveBackup': True, 'HyperBackup': True, 'HyperBackupVault': True}
    collector.active_backup_session = None
    collector.hyper_backup_session = None
    assert list(collector.collect()) == ['hello', 'beautiful', 'world']
