#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.
#

import ConfigParser
import importlib
import logging
import os

DRIVER_LOG = 'log'
DRIVER_MAIL = 'mail'
DRIVER_REST_API = 'restapi'
DRIVERS = [DRIVER_LOG, DRIVER_MAIL, DRIVER_REST_API]

SECTION_NAME = 'monitor'

_default_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    os.pardir,
                                    'etc',
                                    'monitor.conf')
_cf = ConfigParser.ConfigParser()
_cf.read(_default_config_file)


def _get_monitor_section_items():
    """Get all of items of monitor section."""
    items = _cf.items(SECTION_NAME)
    return {item[0]: item[1] for item in items}


class Driver(object):
    """The driver for send message"""
    _driver_type = None
    _driver = None

    def __init__(self, model_name):
        """Init driver
        :param string model_name: nova or cinder...etc.
        """
        self._driver_type = _cf.get(model_name, 'driver')
        if self._driver_type in DRIVERS:
            if self._driver_type == DRIVER_LOG:
                self._driver = _get_monitor_logger(model_name)
            elif self._driver_type == DRIVER_MAIL:
                pass
            else:
                pass
        else:
            raise ValueError('Can not find value[%s] in %s.'
                             % (self._driver_type, DRIVERS))

    def send_message(self, message):
        """send message
        :param string massage: message context.
        """
        if self._driver_type == DRIVER_LOG:
            self._driver.info(message)
        elif self._driver_type == DRIVER_MAIL:
            pass
        else:
            pass


def _get_monitor_mailer():
    pass


def _get_monitor_restapi():
    pass


def _get_monitor_logger(model_name):
    """get monitor logger
    :param string model_name : log model name
    """
    return _get_timed_logger(_cf.get(model_name, 'log_name'),
                             _cf.get(model_name, 'log_level'),
                             _cf.get(model_name, 'log_formatter', raw=True),
                             _cf.get(model_name, 'log_file_path_name'),
                             _cf.get(model_name, 'log_when'),
                             _cf.getint(model_name, 'log_interval'),
                             _cf.getint(model_name, 'log_backupCount'),
                             _cf.get(model_name, 'log_suffix', raw=True))


def _get_timed_logger(log_name,
                      log_level,
                      log_formatter,
                      log_file_path_name,
                      log_when,
                      log_interval,
                      log_backupCount,
                      log_suffix):
    """get timed logger"""
    logger_level = getattr(logging, log_level)

    logger = logging.getLogger(name=log_name)
    logger.setLevel(logger_level)
    formatter = logging.Formatter(log_formatter)

    log_model = importlib.import_module(_cf.get('DEFAULT', 'log_model'))

    dirname = os.path.split(log_file_path_name)[0]
    if not os.path.isdir(dirname):
        os.makedirs(dirname)

    timed_logger = getattr(log_model, _cf.get('DEFAULT', 'log_class'))(
        filename=log_file_path_name,
        when=log_when,
        interval=log_interval,
        backupCount=log_backupCount)

    timed_logger.suffix = log_suffix
    timed_logger.setLevel(logger_level)
    timed_logger.setFormatter(formatter)

    logger.addHandler(timed_logger)

    return logger


class MonitorBase(object):
    """Basic monitor class"""
    def __init__(self, name):
        self.items = _get_monitor_section_items()
        self.driver = Driver(name)
        self.msgs = "Group[%s] Name[%s] Warning : " \
                    "Use rate of %s is %d%% now, " \
                    "and it's over than %s%%."
        self.targets = {item for item in self.items['tgt_list'].split(',')}


class NovaMonitor(MonitorBase):
    """Nova monitor class"""

    def __init__(self, name):
        super(NovaMonitor, self).__init__(name)

    def do_check(self, items):
        """Disc, memory and vcpu check method.
        :param string items:check target items.
        """
        group = items[0]
        name = items[3]
        local_gb = int(items[4])
        local_gb_used = int(items[5])
        memory_mb = int(items[8])
        memory_mb_used = int(items[9])
        vcpus = int(items[12])
        vcpus_used = int(items[13])

        if ':'.join([group, name]) in self.targets:
            self._check_local_gb(group, name, local_gb, local_gb_used)
            self._check_memory_mb(group, name, memory_mb, memory_mb_used)
            self._check_vcpus(group, name, vcpus, vcpus_used)

    def _check_local_gb(self, group, name, local_gb, local_gb_used):
        """Disc check method.
        :param string group: target group.
        :param string name: target name.
        :param int local_gb: disc total.
        :param int local_gb_used: disc used.
        """
        if 'true' == self.items['local_gb'].lower() and \
            int(self.items['local_gb_alert_used_rate']) \
                <= (local_gb_used * 100 / local_gb):

            message = self.msgs % (group,
                                   name,
                                   'local_gb',
                                   (local_gb_used * 100 / local_gb),
                                   self.items['local_gb_alert_used_rate'])

            self.driver.send_message(message)

    def _check_memory_mb(self, group, name, memory_mb, memory_mb_used):
        """Memory check method.
        :param string group: target group.
        :param string name: target name.
        :param int memory_mb: memory total.
        :param int memory_mb_used: memory used.
        """
        if 'true' == self.items['memory_mb'].lower() and \
            int(self.items['memory_mb_alert_used_rate']) \
                <= (memory_mb_used * 100 / memory_mb):

            message = self.msgs % (group,
                                   name,
                                   'memory_mb',
                                   (memory_mb_used * 100 / memory_mb),
                                   self.items['memory_mb_alert_used_rate'])

            self.driver.send_message(message)

    def _check_vcpus(self, group, name, vcpus, vcpus_used):
        """Vcpus check method.
        :param string group: target group.
        :param string name: target name.
        :param int vcpus: vcpu total.
        :param int vcpus_used: vcpu used.
        """
        if 'true' == self.items['vcpus'].lower() and \
            int(self.items['vcpus_alert_used_rate']) \
                <= (vcpus_used * 100 / vcpus):

            message = self.msgs % (group,
                                   name,
                                   'vcpus',
                                   (vcpus_used * 100 / vcpus),
                                   self.items['vcpus_alert_used_rate'])

            self.driver.send_message(message)
