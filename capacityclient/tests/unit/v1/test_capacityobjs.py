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

import datetime
from exceptions import ValueError
import testtools

from capacityclient.v1 import nova_capacityobjs


class CapacityobjManagerTest(testtools.TestCase):
    """CapacityobjManager Test class.
    """
    def setUp(self):
        """Setup test class.
        """
        super(CapacityobjManagerTest, self).setUp()
        self.mgr = nova_capacityobjs.CapacityobjManager()

    def test_put_resource_info(self):
        """Test get method.
        """
        log_file_path_name = self.mgr.put_resource_info()

        # item count + 1
        item_maxnum = 17

        # Check the item that was output to the log one line at a time
        with open(log_file_path_name, 'r') as log_file:
            for line in log_file:
                line = line.replace('\r', '')
                line = line.replace('\n', '')
                items = line.split(" ")

                # And determines the number of elements to be output to the log
                if len(items) != item_maxnum:
                    raise ValueError('Item count error, required 16 but %s.'
                                     % len(items) - 1)

                # And it determines the display unit of resources
                if not items[0] or (
                        items[0] != 'all' and items[0] != 'per_all' and
                        items[0] != 'az' and items[0] != 'per_az' and
                        items[0] != 'host' and items[0] != 'per_host'):
                    raise ValueError(
                        'Item[0] is None or not group name -> %s.'
                        % items[0])

                # Determining whether the time format
                if not items[1] or not items[2] or\
                        not datetime.datetime.strptime(
                            " ".join([items[1], items[2]]),
                            "%Y-%m-%d %H:%M:%S"):
                    raise ValueError(
                        'datetime is not validity, %s %s.'
                        % (items[1], items[2]))

                # It determines whether or not there is a name for each unit
                if not items[3]:
                    raise ValueError(
                        'Item[3] is None, -> %s.'
                        % items[3])
