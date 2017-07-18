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
"""Interface of called Capacityobj."""

import copy
import datetime
import math

from capacityclient.v1 import get_allocation_ratio
from capacityclient.v1 import get_ar_set_type
from capacityclient.v1 import get_client_info
from capacityclient.v1 import get_error_logger
from capacityclient.v1 import get_log_file_path_name
from capacityclient.v1 import get_logger
from capacityclient.v1.monitor import NovaMonitor

from keystoneclient.v2_0 import client as keystone_client

from keystoneclient.auth.identity import v3
from keystoneclient import session as keystone_client_session
from keystoneclient.v3 import client as keystone_client_v3

from novaclient import client as nova_client

AR_SET_TYPE_CNF = 1

ERROR_LOG = get_error_logger('nova')

setvaluelist = dict(local_gb=0,
                    local_gb_used=0,
                    memory_mb=0,
                    memory_mb_used=0,
                    cpus=0,
                    vcpus=0,
                    vcpus_used=0,
                    local_gb_free=0,
                    local_gb_quota=0,
                    memory_mb_free=0,
                    memory_mb_quota=0,
                    vcpus_free=0,
                    vcpus_quota=0)


def keystoneclient():
    """Get keystone client."""
    username, password, project_id, auth_url, auth_version, \
        user_domain_id, project_domain_id, nova_version, \
        endpoint_type, region_name = get_client_info('account')

    if int(auth_version) < 3:
        return keystone_client.Client(
            username=username,
            password=password,
            tenant_name=project_id,
            auth_url=auth_url)

    return keystone_client_v3.Client(
        username=username,
        password=password,
        tenant_name=project_id,
        auth_url=auth_url,
        user_domain_name=user_domain_id,
        project_domain_name=project_domain_id,
        region_name=region_name)


def novaclient():
    """Get nova client."""
    username, password, project_id, auth_url, auth_version, \
        user_domain_id, project_domain_id, nova_version, \
        endpoint_type, region_name = get_client_info('account')

    if int(auth_version) < 3:
        return nova_client.Client(
            version=nova_version,
            username=username,
            api_key=password,
            project_id=project_id,
            auth_url=auth_url)

    auth = v3.Password(
        auth_url=auth_url,
        username=username,
        password=password,
        project_name=project_id,
        user_domain_name=user_domain_id,
        project_domain_name=project_domain_id)
    session = keystone_client_session.Session(auth=auth,
                                              verify='/path/to/ca.cert')
    return nova_client.Client(
        version=nova_version,
        session=session,
        endpoint_type=endpoint_type,
        region_name=region_name)


class CapacityobjManager(object):
    """Manager class for manipulating Capacity."""
    def put_resource_info(self):
        """The body of the resource acquisition and output processing
        """
        output_path = None

        try:
            ar_set_type = get_ar_set_type()

            # Get the resources of information (total and usage)
            # Get in the HOST unit here
            hypervisors_info = novaclient().hypervisors.list()

            # Get the list of AZ
            availability_zones_info = novaclient().availability_zones.list()

            hypervisors_info = \
                self.set_aggregate_ratio(hypervisors_info,
                                         availability_zones_info,
                                         ar_set_type)

            # Get the upper limit information resources
            # Get only the total amount
            quotas_info = dict(
                local_gb=0,
                memory_mb=0,
                vcpus=0,)

            projects_list = self._get_projects_list()
            for projects in projects_list:
                quotas = novaclient().quotas.get(projects.id)

                quotas_info['vcpus'] += quotas.cores
                quotas_info['memory_mb'] += quotas.ram

            # quotas_info = self.get_quota()

            # Create the output information for each unit to be displayed
            # (ALL, AZ, HOST)
            lsits = []
            lsits.extend(self.format_all(hypervisors_info, quotas_info))
            lsits.extend(self.format_az(hypervisors_info,
                                        availability_zones_info))
            lsits.extend(self.format_host(hypervisors_info))

            # And outputs the obtained information to a file
            self.filewrite(lsits)
            # Threshold check
            self.monitor(lsits)

            output_path = get_log_file_path_name('nova')

        except Exception as e:
            ERROR_LOG.exception(e)

        return output_path

    # Get projects list
    def _get_projects_list(self):
        username, password, project_id, auth_url, auth_version, \
            user_domain_id, project_domain_id, nova_version, \
            endpoint_type, region_name = get_client_info('account')

        if int(auth_version) < 3:
            return keystoneclient().tenants.list()
        return keystoneclient().projects.list()

    # To get the whole amount of resources
    def format_all(self, hypervisors_info, quotas_info):

        # Initialization of the resource information
        valuelist = copy.deepcopy(setvaluelist)

        # To be the total amount, the sum total-usage of each HOST
        for hypervisors in hypervisors_info:
            valuelist['local_gb'] += hypervisors.local_gb
            valuelist['local_gb_used'] += hypervisors.local_gb_used
            valuelist['memory_mb'] += hypervisors.memory_mb
            valuelist['memory_mb_used'] += hypervisors.memory_mb_used
            valuelist['cpus'] += hypervisors.cpus
            valuelist['vcpus'] += hypervisors.vcpus
            valuelist['vcpus_used'] += hypervisors.vcpus_used

        valuelist['local_gb_free'] = \
            valuelist['local_gb'] - valuelist['local_gb_used']
        valuelist['memory_mb_free'] = \
            valuelist['memory_mb'] - valuelist['memory_mb_used']
        valuelist['memory_mb_quota'] = quotas_info["memory_mb"]
        valuelist['vcpus_free'] = \
            valuelist['vcpus'] - valuelist['vcpus_used']
        valuelist['vcpus_quota'] = quotas_info["vcpus"]

        return self.output_format('all', 'ALL', valuelist)

    # Get the resources in the AZ unit
    def format_az(self, hypervisors_info, availability_zones_info):
        outlist = []
        hypervisors_hash_info = {}

        # Convert to hash. Put the string in the HOST name
        for hypervisors in hypervisors_info:
            h_hostname = hypervisors.hypervisor_hostname
            hypervisors_hash_info[h_hostname] = hypervisors

        # Calculate the total amount and use amount for each AZ, acquisition
        for az in availability_zones_info:

            az_name = az.zoneName

            if 'internal' == az_name:
                continue

            # Initialize
            valuelist = copy.deepcopy(setvaluelist)

            # The sum of the total amount and use the amount to be a AZ unit
            hosts = az.hosts
            for hostname in hosts.keys():

                if hostname in hypervisors_hash_info:
                    valuelist['local_gb'] \
                        += hypervisors_hash_info[hostname].local_gb
                    valuelist['local_gb_used'] \
                        += hypervisors_hash_info[hostname].local_gb_used
                    valuelist['memory_mb'] \
                        += hypervisors_hash_info[hostname].memory_mb
                    valuelist['memory_mb_used'] \
                        += hypervisors_hash_info[hostname].memory_mb_used
                    valuelist['cpus'] \
                        += hypervisors_hash_info[hostname].cpus
                    valuelist['vcpus'] \
                        += hypervisors_hash_info[hostname].vcpus
                    valuelist['vcpus_used'] \
                        += hypervisors_hash_info[hostname].vcpus_used

            valuelist['local_gb_free'] = \
                valuelist['local_gb'] - valuelist['local_gb_used']
            valuelist['memory_mb_free'] = \
                valuelist['memory_mb'] - valuelist['memory_mb_used']
            valuelist['vcpus_free'] = \
                valuelist['vcpus'] - valuelist['vcpus_used']

            outlist.extend(self.output_format('az', az_name, valuelist))

        return outlist

    # Get the resources in the HOST unit
    def format_host(self, hypervisors_info):
        outlist = []

        # Calculate the total amount and use amount for each AZ, acquisition
        for hypervisors in hypervisors_info:

            host_name = hypervisors.hypervisor_hostname

            # Initialize
            valuelist = copy.deepcopy(setvaluelist)

            # The sum of the total amount and use the amount to be a HOST unit
            valuelist['local_gb'] += hypervisors.local_gb
            valuelist['local_gb_used'] += hypervisors.local_gb_used
            valuelist['memory_mb'] += hypervisors.memory_mb
            valuelist['memory_mb_used'] += hypervisors.memory_mb_used
            valuelist['cpus'] += hypervisors.cpus
            valuelist['vcpus'] += hypervisors.vcpus
            valuelist['vcpus_used'] += hypervisors.vcpus_used

            valuelist['local_gb_free'] = \
                valuelist['local_gb'] - valuelist['local_gb_used']
            valuelist['memory_mb_free'] = \
                valuelist['memory_mb'] - valuelist['memory_mb_used']
            valuelist['vcpus_free'] = \
                valuelist['vcpus'] - valuelist['vcpus_used']

            outlist.extend(self.output_format('host', host_name, valuelist))

        return outlist

    # Get the upper limit of resources
    def get_quota(self):

        # To get the whole of the resource limit (quota)
        limits = novaclient().limits.get().absolute
        quotas_info = {}

        # String with the name and the upper limit for each type of resource
        for limit in limits:
            quotas_info[limit.name] = limit.value
        return quotas_info

    # The molded the resource information in the form of output format
    def output_format(self, group, name, valuelist):

        outlist = []
        numlist = '{0} {1} {2} {3} {4} {5} {6} {7} ' \
            '{8} {9} {10} {11} {12} {13} {14} {15}'

        # Enter the data to usage of format
        # {0} group: Unit
        #    (whole: all or per_all, AZ: az or per_az, host: host or per_host)
        # {1} datetime: date and time ("% Y-% m-% d% H:% M:% S")
        # {2} name: The name (whole: ALL, AZ: az name, host: Host name)
        # {3} local_gb: disk total amount (GByte)
        # {4} local_gb_used: disk usage (GByte)
        # {5} local_gb_free: free disk space (GByte)
        # {6} local_gb_quota: disk upper limit (GByte)
        #    * Unit (whole: all) only set when, otherwise fixed to 0
        # {7} memory_mb: total amount of memory (MByte)
        # {8} memory_mb_used: memory usage (MByte)
        # {9} memory_mb_free: memory free (MByte)
        # {10} memory_mb_quota: memory upper limit value (MByte)
        #     * Unit (whole: all) only set when, otherwise fixed to 0
        # {11} cpus: Physical cpus
        # {12} vcpus: CPU total
        # {13} vcpus_used: CPU usage
        # {14} vcpus_free: CPU free
        # {15} vcpus_quota: CPU upper limit
        #     * Unit (whole: all) only set when, otherwise fixed to 0
        outlist.append(numlist.format(
            str(group),
            str(datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")),
            str(name),
            str(valuelist["local_gb"]),
            str(valuelist["local_gb_used"]),
            str(valuelist["local_gb_free"]),
            str(valuelist["local_gb_quota"]),
            str(valuelist["memory_mb"]),
            str(valuelist["memory_mb_used"]),
            str(valuelist["memory_mb_free"]),
            str(valuelist["memory_mb_quota"]),
            str(valuelist["cpus"]),
            str(valuelist["vcpus"]),
            str(valuelist["vcpus_used"]),
            str(valuelist["vcpus_free"]),
            str(valuelist["vcpus_quota"])))

        # Enter the data into the format of percent unit
        # {3} local_gb: to 100% at a fixed
        # {4} local_gb_used: disk utilization
        # Formula: (total disk / disk usage) * 100 = disk utilization
        # {5} local_gb_free: disk free rate
        # Formula: 100 - (disk total / disk usage) * 100 = disk free rate
        # {6} local_gb_quota: 0 fixed
        # {7} memory_mb: to 100% at a fixed
        # {8} memory_mb_used: memory utilization
        # Formula: (total memory / memory usage) * 100 = memory utilization
        # {9} memory_mb_free: memory free rate
        # Formula: 100 - (total memory / memory usage) * 100 = memory free rate
        # {10} memory_mb_quota: 0 fixed
        # {11} cpus: Physical cpus
        # {12} vcpus: to 100% at a fixed
        # {13} vcpus_used: CPU utilization
        # Formula: (CPU total / CPU usage) * 100 = CPU utilization
        # {14} vcpus_free: CPU free rate
        # Formula: 100 - (CPU total / CPU usage) * 100 = CPU free rate
        # {15} vcpus_quota: 0 fixed

        per_gb = float(valuelist['local_gb_used']) / valuelist['local_gb']
        per_mem = float(valuelist['memory_mb_used']) / valuelist['memory_mb']
        per_cpu = float(valuelist['vcpus_used']) / valuelist['vcpus']
        per_p_cpu = float(valuelist['cpus']) / valuelist['vcpus']

        outlist.append(numlist.format(
            str('per_' + group),
            str(datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")),
            str(name),
            '100',
            str(int(math.ceil(per_gb * 100))),
            str(100 - int(math.ceil(per_gb * 100))),
            '0',
            '100',
            str(int(math.ceil(per_mem * 100))),
            str(100 - int(math.ceil(per_mem * 100))),
            '0',
            str(int(math.ceil(per_p_cpu * 100))),
            '100',
            str(int(math.ceil(per_cpu * 100))),
            str(100 - int(math.ceil(per_cpu * 100))),
            '0'))

        return outlist

    # Output the resource information in the file
    def filewrite(self, output):
        LOG = get_logger('nova')

        for line in output:
            LOG.info(line)

    # Threshold check
    def monitor(self, output):
        monitor = NovaMonitor('nova')

        for line in output:
            monitor.do_check(line.split(' '))

    def set_aggregate_ratio(self,
                            hypervisors_info,
                            availability_zones_info,
                            set_type=AR_SET_TYPE_CNF):
        """Set aggregate ratio
        :param hypervisors_info: hypervisors info
        :param availability_zones_info: ziones info
        :param set_type: call method type
        """
        if set_type == AR_SET_TYPE_CNF:
            return self.set_aggregate_ratio_by_config(hypervisors_info,
                                                      availability_zones_info)
        else:
            return self.set_aggregate_ratio_defualt(hypervisors_info)

    def set_aggregate_ratio_by_config(self,
                                      hypervisors_info,
                                      availability_zones_info):
        """Overwrite CPU, memory and disc for each host
        the actual value with the value of the setting
        :param hypervisors_info: hypervisors info
        :param availability_zones_info: ziones info
        """
        changed_hypervisors_info = []

        for hypervisor in hypervisors_info:
            disk_allocation_ratio = 1
            ram_allocation_ratio = 1
            cpu_allocation_ratio = 1

            for az in availability_zones_info:
                az_name = az.zoneName

                if hypervisor.hypervisor_hostname in az.hosts:
                    try:
                        disk_allocation_ratio = \
                            get_allocation_ratio('disk_allocation_ratio',
                                                 az_name)
                    except Exception as e:
                        ERROR_LOG.warning(e)
                        disk_allocation_ratio = 1

                    try:
                        ram_allocation_ratio = \
                            get_allocation_ratio('ram_allocation_ratio',
                                                 az_name)
                    except Exception as e:
                        ERROR_LOG.warning(e)
                        ram_allocation_ratio = 1

                    try:
                        cpu_allocation_ratio = \
                            get_allocation_ratio('cpu_allocation_ratio',
                                                 az_name)
                    except Exception as e:
                        ERROR_LOG.warning(e)
                        cpu_allocation_ratio = 1

                    break

            # Using metadata , the hypervisor CPU and memory and disk
            # re- calculate the size .
            # After calculation disk = disk * disk_allocation_ratio
            hypervisor.local_gb = int(
                hypervisor.local_gb * disk_allocation_ratio)
            # After calculation of memory = memory * ram_allocation_ratio
            hypervisor.memory_mb = int(
                hypervisor.memory_mb * ram_allocation_ratio)
            # Physical cpus
            hypervisor.cpus = hypervisor.vcpus
            # After calculation of CPU = CPU * cpu_allocation_ratio
            hypervisor.vcpus = int(
                hypervisor.vcpus * cpu_allocation_ratio)

            # Add a hypervisor that was overwritten by the calculation results
            changed_hypervisors_info.append(hypervisor)

        # The return worked hypervisors_info
        return changed_hypervisors_info

    # Overwrite CPU, memory and disc for each host
    # get value from the actual meta data of nova
    def set_aggregate_ratio_defualt(self, hypervisors_info):
        """Overwrite CPU, memory and disc for each host
        the actual value with the value of the setting
        :param hypervisors_info: hypervisors info
        """
        # Initialization of the return value
        changed_hypervisors_info = []

        # host aggregate list acquisition of nova
        aggregates_list = []
        for aggregate in novaclient().aggregates.list():
            aggregates_list.append(
                novaclient().aggregates.get_details(aggregate.id))

        # loop hypervisors_info
        for hypervisor in hypervisors_info:

            # 1 initialized
            disk_allocation_ratio = 1
            ram_allocation_ratio = 1
            cpu_allocation_ratio = 1

            # hypervisor is I look for or belong to any host aggregate
            for aggregate in aggregates_list:

                # If the host name belongs to a host aggregates ,
                # to obtain the ratio of metadata
                if hypervisor.hypervisor_hostname in aggregate.hosts:
                    disk_allocation_ratio = float(
                        aggregate.metadata.get('disk_allocation_ratio', 1))
                    ram_allocation_ratio = float(
                        aggregate.metadata.get('ram_allocation_ratio', 1))
                    cpu_allocation_ratio = float(
                        aggregate.metadata.get('cpu_allocation_ratio', 1))

                break

            # Using metadata , the hypervisor CPU and memory and disk
            # re- calculate the size .
            # After calculation disk = disk * disk_allocation_ratio
            hypervisor.local_gb = int(
                hypervisor.local_gb * disk_allocation_ratio)
            # After calculation of memory = memory * ram_allocation_ratio
            hypervisor.memory_mb = int(
                hypervisor.memory_mb * ram_allocation_ratio)
            # Physical cpus
            hypervisor.cpus = hypervisor.vcpus
            # After calculation of CPU = CPU * cpu_allocation_ratio
            hypervisor.vcpus = int(
                hypervisor.vcpus * cpu_allocation_ratio)

            # Add a hypervisor that was overwritten by the calculation results
            changed_hypervisors_info.append(hypervisor)

        # The return worked hypervisors_info
        return changed_hypervisors_info

# Main processing
if __name__ == '__main__':
    CapacityobjManager().put_resource_info()
