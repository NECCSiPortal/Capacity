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

_default_config_file = \
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + '/..',
                 'etc',
                 'capacityclient-config.conf')

_cf = ConfigParser.ConfigParser()
_cf.read(_default_config_file)


def get_ar_set_type():
    '''Get aggregate ratio set type.'''
    return _cf.getint('DEFAULT', 'ar_set_type')


def get_allocation_ratio(section, az_name):
    '''Get aggregate ratio
        :param section: section name
        :param az_name: availability zone name
    '''
    return _cf.getint(section, az_name)


def get_log_file_path_name(model_name):
    '''get full path name of log file
        @type  string
        @param model_name log model name
    '''
    return _cf.get(model_name, 'log_file_path_name')


def get_client_info(model_name):
    '''get client information
        @type  string
        @param model_name log model name
    '''
    return _cf.get(model_name, 'client_user'), \
        _cf.get(model_name, 'client_password'), \
        _cf.get(model_name, 'client_project_id'), \
        _cf.get(model_name, 'client_auth_url'), \
        _cf.get(model_name, 'client_auth_version'), \
        _cf.get(model_name, 'client_user_domain_id'), \
        _cf.get(model_name, 'client_project_domain_id'), \
        _cf.get(model_name, 'client_nova_version'), \
        _cf.get(model_name, 'client_nova_endpoint_type'), \
        _cf.get(model_name, 'client_nova_region_name'),


def get_logger(model_name):
    '''get logger
        @type  string
        @param model_name log model name
    '''
    return _get_timed_logger(_cf.get(model_name, 'log_name'),
                             _cf.get(model_name, 'log_level'),
                             _cf.get(model_name, 'log_formatter', raw=True),
                             _cf.get(model_name, 'log_file_path_name'),
                             _cf.get(model_name, 'log_when'),
                             _cf.getint(model_name, 'log_interval'),
                             _cf.getint(model_name, 'log_backupCount'),
                             _cf.get(model_name, 'log_suffix', raw=True))


def get_error_logger(model_name):
    '''get error logger
        @type  string
        @param model_name log model name
    '''
    return _get_timed_logger(_cf.get(model_name, 'error_log_name'),
                             _cf.get(model_name, 'error_log_level'),
                             _cf.get(model_name, 'error_log_formatter',
                                     raw=True),
                             _cf.get(model_name, 'error_log_file_path_name'),
                             _cf.get(model_name, 'error_log_when'),
                             _cf.getint(model_name, 'error_log_interval'),
                             _cf.getint(model_name, 'error_log_backupCount'),
                             _cf.get(model_name, 'error_log_suffix', raw=True))


def _get_timed_logger(log_name,
                      log_level,
                      log_formatter,
                      log_file_path_name,
                      log_when,
                      log_interval,
                      log_backupCount,
                      log_suffix):
    '''get timed logger
    '''
    logger_level = eval('logging.%s' % log_level)

    logger = logging.getLogger(name=log_name)
    logger.setLevel(logger_level)
    formatter = logging.Formatter(log_formatter)

    log_model = importlib.import_module(_cf.get('DEFAULT', 'log_model'))

    dirname, filename = os.path.split(log_file_path_name)
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
