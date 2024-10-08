#!/usr/bin/env python
import datetime
import json
import os
import time

from prometheus_client import start_http_server
from prometheus_client.metrics_core import GaugeMetricFamily
from prometheus_client.registry import Collector, REGISTRY
# import sys
# sys.path.insert(0, '/home/raphael/Projekte/synology-api')
from synology_api import core_active_backup as active_backup
from synology_api import core_backup as hyper_backup


def active_backup_get_info(active_backup_session):
    abb_hypervisor = active_backup_session.list_vm_hypervisor()
    abb_vms = active_backup_session.list_device_transfer_size()

    active_backup_lastbackup_timestamp = GaugeMetricFamily(
        "synology_active_backup_lastbackup_timestamp",
        "Timestamp of last backup",
        labels=["vmname", "hostname", "vmuuid", "vmos"],
    )
    active_backup_lastbackup_duration = GaugeMetricFamily(
        "synology_active_backup_lastbackup_duration",
        "Duration of last backup in Seconds",
        labels=["vmname", "hostname", "vmuuid", "vmos"],
    )
    active_backup_lastbackup_transfered_bytes = GaugeMetricFamily(
        "synology_active_backup_lastbackup_transfered_bytes",
        "Transfered data of last backup in Bytes",
        labels=["vmname", "hostname", "vmuuid", "vmos"],
    )
    active_backup_lastbackup_result = GaugeMetricFamily(
        "synology_active_backup_lastbackup_result",
        "Result of last backup - 2 = Good, 4 = Bad",
        labels=["vmname", "hostname", "vmuuid", "vmos"],
    )

    hypervisor_list = {}

    for hypervisor in abb_hypervisor["data"]:
        hypervisor_list[hypervisor["inventory_id"]] = hypervisor["host_name"]

    for vm in abb_vms["data"]["device_list"]:
        if vm["device"]["inventory_id"] != 0:
            vm_hypervisor = hypervisor_list[vm["device"]["inventory_id"]]
        else:
            vm_hypervisor = vm["device"]["host_name"]

        vm_hostname = vm["device"]["host_name"]
        vm_uuid = vm["device"]["device_uuid"]
        vm_os = vm["device"]["os_name"]

        try:  # trying, if no backup is existing, this will fail.
            if vm["transfer_list"]:
                vm_backup_start_timestamp = vm["transfer_list"][0]["time_start"]
                vm_backup_end_timestamp = vm["transfer_list"][0]["time_end"]
                vm_backup_duration_seconds = vm_backup_end_timestamp - vm_backup_start_timestamp
                vm_backup_status = vm["transfer_list"][0]["status"]
                vm_backup_transfered_bytes = vm["transfer_list"][0]["transfered_bytes"]
                active_backup_lastbackup_timestamp.add_metric(
                    [vm_hostname, vm_hypervisor, vm_uuid, vm_os], vm_backup_end_timestamp
                )
                yield active_backup_lastbackup_timestamp
                active_backup_lastbackup_duration.add_metric(
                    [vm_hostname, vm_hypervisor, vm_uuid, vm_os], vm_backup_duration_seconds
                )
                yield active_backup_lastbackup_duration
                active_backup_lastbackup_transfered_bytes.add_metric(
                    [vm_hostname, vm_hypervisor, vm_uuid, vm_os], vm_backup_transfered_bytes
                )
                yield active_backup_lastbackup_transfered_bytes
                active_backup_lastbackup_result.add_metric(
                    [vm_hostname, vm_hypervisor, vm_uuid, vm_os], vm_backup_status
                )
                yield active_backup_lastbackup_result
        except IndexError:
            print("ERROR - Failed to load Backups.")


def convert_to_bool(input_):
    # distutils.util.strtobool is deprecated, and according to PEP 632
    # the suggestion is "you will need to reimplement the functionality yourself"
    match input_:
        case "True" | "true" | "t" | "yes" | "y" | "1":
            return True
        case _:
            return False


def convert_to_int(input_):
    return int(input_)


def hyper_backup_get_info(hyper_backup_session):
    hyper_backup_data = hyper_backup_session.backup_task_list()
    hyper_backup_lastbackup_successful_timestamp = GaugeMetricFamily(
        "synology_hyper_backup_lastbackup_successful_timestamp",
        "Timestamp of last successful backup",
        labels=["task_id", "task_name", "target_type"],
    )
    hyper_backup_lastbackup_timestamp = GaugeMetricFamily(
        "synology_hyper_backup_lastbackup_timestamp",
        "Timestamp of last backup",
        labels=["task_id", "task_name", "target_type"],
    )
    hyper_backup_lastbackup_duration = GaugeMetricFamily(
        "synology_hyper_backup_lastbackup_duration",
        "Duration of last backup in Seconds",
        labels=["task_id", "task_name", "target_type"],
    )

    hyper_backup_tasklist = {}
    hyper_backup_taskname = {}
    hyper_backup_tasktype = {}

    time_format_with_seconds = "%Y/%m/%d %H:%M:%S"
    time_format_without_seconds = "%Y/%m/%d %H:%M"

    for task in hyper_backup_data["data"]["task_list"]:
        hyper_backup_tasklist[task["task_id"]] = str(task["task_id"])
        hyper_backup_taskname[task["task_id"]] = task["name"]
        hyper_backup_tasktype[task["task_id"]] = task["target_type"]

    for result in hyper_backup_tasklist:
        hyper_backup_taskresult = hyper_backup_session.backup_task_result(result)

        hyper_backup_last_success = hyper_backup_taskresult["data"]["last_bkp_success_time"]  # last success

        if hyper_backup_last_success == "":  # if the backup has never completed, set the time to now
            hyper_backup_last_success = datetime.datetime.now().strftime(time_format_with_seconds)

        try:
            hyper_backup_last_success_timestamp = time.mktime(
                time.strptime(hyper_backup_last_success, time_format_with_seconds)
            )
        except ValueError:
            hyper_backup_last_success_timestamp = time.mktime(
                time.strptime(hyper_backup_last_success, time_format_without_seconds)
            )

        hyper_backup_start_time = hyper_backup_taskresult["data"]["last_bkp_time"]
        hyper_backup_end_time = hyper_backup_taskresult["data"]["last_bkp_end_time"]

        if hyper_backup_start_time == "":  # if the backup has never completed, set the time to now
            hyper_backup_start_time = datetime.datetime.now().strftime(time_format_with_seconds)

        if hyper_backup_end_time == "":  # if the backup has never completed, set the time to now
            hyper_backup_end_time = datetime.datetime.now().strftime(time_format_with_seconds)

        try:
            hyper_backup_start_timestamp = time.mktime(time.strptime(hyper_backup_start_time, time_format_with_seconds))
        except ValueError:
            hyper_backup_start_timestamp = time.mktime(
                time.strptime(hyper_backup_start_time, time_format_without_seconds)
            )

        try:
            hyper_backup_end_timestamp = time.mktime(time.strptime(hyper_backup_end_time, time_format_with_seconds))
        except ValueError:
            hyper_backup_end_timestamp = time.mktime(time.strptime(hyper_backup_end_time, time_format_without_seconds))

        hyper_backup_duration_seconds = hyper_backup_end_timestamp - hyper_backup_start_timestamp

        try:
            hyper_backup_lastbackup_successful_timestamp.add_metric(
                [
                    hyper_backup_tasklist[result],
                    hyper_backup_taskname[result],
                    hyper_backup_tasktype[result],
                ],
                hyper_backup_last_success_timestamp,
            )
            yield hyper_backup_lastbackup_successful_timestamp
            hyper_backup_lastbackup_timestamp.add_metric(
                [
                    hyper_backup_tasklist[result],
                    hyper_backup_taskname[result],
                    hyper_backup_tasktype[result],
                ],
                hyper_backup_end_timestamp,
            )
            yield hyper_backup_lastbackup_timestamp
            hyper_backup_lastbackup_duration.add_metric(
                [
                    hyper_backup_tasklist[result],
                    hyper_backup_taskname[result],
                    hyper_backup_tasktype[result],
                ],
                hyper_backup_duration_seconds,
            )
            yield hyper_backup_lastbackup_duration
        except IndexError:
            print("ERROR - Failed to load Backups.")


def hyper_backup_vault_get_info(hyper_backup_vault_session):
    hyper_backup_vault_last_backup_duration_seconds = GaugeMetricFamily(
        "synology_hyper_backup_vault_last_backup_duration_seconds",
        "Duration of last backup",
        labels=["target_name", "target_id", "target_status"],
    )
    hyper_backup_vault_last_backup_start_timestamp = GaugeMetricFamily(
        "synology_hyper_backup_vault_last_backup_start_timestamp",
        "Timestamp of last backup start",
        labels=["target_name", "target_id", "target_status"],
    )
    hyper_backup_vault_target_used_size_bytes = GaugeMetricFamily(
        "synology_hyper_backup_vault_target_used_size_bytes",
        "Size of last backup",
        labels=["target_name", "target_id", "target_status"],
    )
    hyper_backup_vault_data = hyper_backup_vault_session.vault_target_list()

    for target in hyper_backup_vault_data["data"]["target_list"]:
        hyper_backup_vault_target_name = target["target_name"]
        hyper_backup_vault_target_id = target["target_id"]
        hyper_backup_vault_target_status = target["status"]
        hyper_backup_vault_target_last_backup_duration = target["last_backup_duration"]
        hyper_backup_vault_target_last_backup_start_time = target["last_backup_start_time"]
        hyper_backup_vault_target_used_size_kibibytes = target["used_size"]
        hyper_backup_vault_target_used_size_in_bytes = hyper_backup_vault_target_used_size_kibibytes * 1024
        hyper_backup_vault_last_backup_duration_seconds.add_metric(
            [
                hyper_backup_vault_target_name,
                hyper_backup_vault_target_id,
                hyper_backup_vault_target_status,
            ],
            hyper_backup_vault_target_last_backup_duration,
        )
        yield hyper_backup_vault_last_backup_duration_seconds
        hyper_backup_vault_last_backup_start_timestamp.add_metric(
            [
                hyper_backup_vault_target_name,
                hyper_backup_vault_target_id,
                hyper_backup_vault_target_status,
            ],
            hyper_backup_vault_target_last_backup_start_time,
        )
        yield hyper_backup_vault_last_backup_start_timestamp
        hyper_backup_vault_target_used_size_bytes.add_metric(
            [
                hyper_backup_vault_target_name,
                hyper_backup_vault_target_id,
                hyper_backup_vault_target_status,
            ],
            hyper_backup_vault_target_used_size_in_bytes,
        )
        yield hyper_backup_vault_target_used_size_bytes


class BackupsCollector(Collector):
    def __init__(self, config, creds):
        self.config = config
        if config["ActiveBackup"]:
            self.active_backup_session = active_backup.ActiveBackupBusiness(*creds)

        if config["HyperBackup"] or config["HyperBackupVault"]:
            self.hyper_backup_session = hyper_backup.Backup(*creds)

    def collect(self):
        print("collect called")
        if self.config["ActiveBackup"]:
            yield from active_backup_get_info(self.active_backup_session)

        if self.config["HyperBackup"]:
            yield from hyper_backup_get_info(self.hyper_backup_session)

        if self.config["HyperBackupVault"]:
            yield from hyper_backup_vault_get_info(self.hyper_backup_session)


def get_config(config_file_name="config.json"):
    config_items_and_types = {
        "DSMAddress": "string",
        "DSMPort": "int",
        "Username": "string",
        "Password": "string",
        "Secure": "bool",
        "Cert_Verify": "bool",
        "ActiveBackup": "bool",
        "HyperBackup": "bool",
        "HyperBackupVault": "bool",
        "ExporterPort": "int",
        "DSM_Version": "int",
    }

    if os.path.exists(config_file_name):
        with open(config_file_name) as config_file:
            config = json.load(config_file)
    else:
        config = {}

    for config_item, item_type in config_items_and_types.items():
        if config_item not in config:
            config_item_env_var = config_item.upper()
            print(
                f"Configuration item '{config_item}' wasn't found in {config_file_name}"
                ", attempting to read from "
                "environnment variable '{config_item_env_var}'"
            )
            match item_type:
                case "string":
                    config[config_item] = os.getenv(config_item_env_var)
                case "bool":
                    config[config_item] = convert_to_bool(os.getenv(config_item_env_var))
                case "int":
                    config[config_item] = convert_to_int(os.getenv(config_item_env_var))
                case _:
                    print("ERROR - Invalid configuration type, exiting")
                    exit(1)

    missing_config_items = [key for key in config_items_and_types if config.get(key) is None]
    if missing_config_items:
        print(
            f"ERROR - Missing or bad configuration for {missing_config_items},"
            f"it couldn't be found in {config_file_name}"
            "or in any environment variables, exiting"
        )
        exit(1)

    if "Address" not in config:
        config["Address"] = "0.0.0.0"
    creds = (
        config["DSMAddress"],
        config["DSMPort"],
        config["Username"],
        config["Password"],
        config["Secure"],
        config["Cert_Verify"],
        config["DSM_Version"]
    )
    return config, creds


if __name__ == "__main__":
    config, creds = get_config()
    print("Synology Backup Exporter")
    print("2024 - raphii / Raphael Pertl")
    # Start up the server to expose the metrics.
    REGISTRY.register(BackupsCollector(config, creds))
    start_http_server(int(config["ExporterPort"]), config["Address"])
    print("INFO - Web Server running on Port " + str(config["ExporterPort"]))
    while True:
        # wait, server is in a thread started in start_http_server
        time.sleep(60)

