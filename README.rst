=============
Capacity Tool
=============
This tool collects a consumption of the resource
from OpenStack Keystone and Nova, and outputs a log file.

How to use
==========

Install script
--------------

Install command::

    # cd <install_dir>
    # tar xvfz Capacity.tar.gz
    # mkdir -p /var/log/capacity/nova
    # chmod 755 /var/log/capacity/nova
    # vi Capacity.git/capacityclient/etc/capacityclient-config.conf
        Set account section and nova section.
    # pip install Capacity.git/requirements.txt

Manual Run
----------

run command::

    # PYTHONPATH=<install_dir>/Capacity python "<install_dir>/Capacity.git/capacityclient/v1/nova_capacityobjs.py"

Auto Run
--------

You use cron on Red Hat Linux.

A cron setting example::

    PYTHONPATH=:<install_dir>/Capacity.git

    # Ansible: capacity client setting
    15 15 * * * python "<install_dir>/Capacity.git/capacityclient/v1/nova_capacityobjs.py"

Run Unit Test
=============

run unit test command::

    # pip install Capacity/test-requirements.txt
    # ./run_tests.sh
