#!/usr/bin/env python

import collections
import json
import os
import socket
import subprocess
import sys
import time

try:
    # Python 3
    from urllib.request import urlopen, URLError, HTTPError
except ImportError:
    # Python 2
    from urllib2 import urlopen, URLError, HTTPError


SanityCheckResult = collections.namedtuple(
    'SanityCheckResult', ['is_ok', 'message']
)


# (string, string)
Mount = collections.namedtuple("Mount", ['mount', 'device'])


DEFAULT_PORT_RETRIES = 2
DEFAULT_PORT_RETRY_DELAY = 5
DEFAULT_HTTP_RETRIES = 3
DEFAULT_HTTP_RETRY_DELAY = 1


def is_port_open(host, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(.1)
        s.connect((host, port))
        s.shutdown(socket.SHUT_RDWR)
        return True
    except socket.error:
        return False


def check_port(host, port, retries=DEFAULT_PORT_RETRIES, retry_delay=DEFAULT_PORT_RETRY_DELAY):
    if is_port_open(host, port):
        return True
    retry_number = 1
    while retry_number <= retries:
        time.sleep(retry_delay)
        if is_port_open(host, port):
            return True
        retry_number += 1
    return False


def run_command(command):
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return True, output
    except subprocess.CalledProcessError as error:
        return False, error.output


def get_free_percentage_on_mount(mount):
    stats = os.statvfs(mount)
    return stats.f_bavail / float(stats.f_blocks) * 100


def test_free_space_on_mount(mount, free_percentage_required):
    free_percentage = get_free_percentage_on_mount(mount)
    if free_percentage_required > free_percentage:
        message = "Not enough free space on {mount}. Free space is {percentage:.1f}%".format(
            mount=mount,
            percentage=free_percentage
        )
        return SanityCheckResult(False, message)
    message = "Enough free space {mount}. Free space is {percentage:.1f}%".format(
        mount=mount,
        percentage=free_percentage
    )
    return SanityCheckResult(True, message)


def send_message(recipient, subject, body):
    """
    While sending mail is not reliable, mail delivery is async, and mail always
    exits successfully.
    """
    process = subprocess.Popen(['mail', '-s', subject, recipient], stdin=subprocess.PIPE)
    process.communicate(body)


def get_dev_mounts():
    """
    Return a list of mounted drives.
    Uses heuristics to only return mounts that we want to check for free space.
    """

    results = []

    with open("/proc/mounts") as f:
        for line in f:
            if not line.strip():
                continue

            parts = line.split()
            mount = Mount(parts[1], parts[0])

            # /dev/loopX devices are mounted images that are expected to be 100% full,
            # so we don't want to monitor those. Snapd uses these extensively.
            if mount.device.startswith("/dev/loop"):
                continue

            # Standard /dev/ devices.
            elif mount.device.startswith("/dev"):
                results.append(mount)

            # Special cases, but also used by the system. There was a
            # problem with a device named `mysql` in some SoYouStart instances, so this is an extra check to also
            # find some devices with special names but mounted in a folder used by the system (`/var/` in this case)
            # Skip /var/lib/lxcfs, which can exist as a special fuse mount used for lxc.
            elif mount.mount.startswith("/var/") and mount.mount != "/var/lib/lxcfs":
                results.append(mount)

    return results


def test_global_free_percentage(default_free_space_percentage):
    for mount in get_dev_mounts():
        yield test_free_space_on_mount(mount.mount, default_free_space_percentage)


def test_ports(ports):
    response = []
    for port_config in ports:
        host, port = port_config['host'], int(port_config['port'])
        message = port_config['message']
        retries = int(port_config.get('retries', DEFAULT_PORT_RETRIES))
        retry_delay = float(port_config.get('retry_delay', DEFAULT_PORT_RETRY_DELAY))
        if not check_port(host, port, retries=retries, retry_delay=retry_delay):
            response.append(SanityCheckResult(False, message))
        else:
            message = "Port {}:{} is getting connections".format(host, port)
            response.append(SanityCheckResult(True, message))
    return response


def test_commands(commands):
    response = []
    for command in commands:
        command_passed, command_output = run_command(command['command'])
        if command_passed:
            command_message = "Command {} returned exit status 0".format(command['command'])
        else:
            command_message = command['message']
        response.append(SanityCheckResult(command_passed, '{}\n{}'.format(command_message, command_output)))
    return response


def report_is_ok(report):
    return all(check.is_ok for check in report)


def format_report(report):
    lines = []
    report = sorted(report, key= lambda check: check.is_ok)
    for check in report:
        status = "OK" if check.is_ok else "ERROR"
        lines.append("#. {status} {message}".format(status=status, message=check.message))
    return "\n".join(lines)


def sanity_check(json_data):
    report = []
    report.extend(
        test_global_free_percentage(float(json_data['free_percentage']))
    )
    report.extend(
        test_ports(json_data['ports'])
    )
    report.extend(
        test_commands(json_data['commands'])
    )

    if report_is_ok(report):
        if json_data.get('snitch'):
            report.extend(
                ping_http_endpoint(json_data['snitch'])
            )

    if not report_is_ok(report):
        report_text = format_report(report)
        send_message(json_data['send_report_to'], json_data['subject'], report_text)

    with open(json_data['report_file'], 'w') as f:
        report_text = format_report(report)
        f.write(report_text)


def ping_http_endpoint(url, max_retries=DEFAULT_HTTP_RETRIES, delay=DEFAULT_HTTP_RETRY_DELAY):
    report = []
    for count in range(1, max_retries + 1):
        try:
            response = urlopen(url, timeout=5)
        except (URLError, HTTPError) as e:
            report.append(SanityCheckResult(True, "Attempt {} to contact DMS failed due to:"
                                                  "\n{}".format(count, str(e))))
        else:
            if 200 <= response.getcode() < 300:
                report.append(SanityCheckResult(True, "Attempt {} to contact DMS succeeded.".format(count)))
                break
            report.append(SanityCheckResult(True, "Attempt {} to contact DMS returned code "
                                                  "{}".format(count, response.getcode())))
        time.sleep(delay)
    else:
        report.append(SanityCheckResult(False, "Couldn't send snitch after {} attempts".format(max_retries)))
    return report

if __name__ == "__main__":
    data_file = sys.argv[1]
    with open(data_file, 'r') as f:
        json_data = json.load(f)
    sanity_check(json_data)
