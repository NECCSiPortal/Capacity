
================
Develop Note
================
CREATE 2015/06/02
UPDATE 2015/06/02 INSTALL & UNINSTALL
UPDATE 2015/06/05 COMMANDLINE TEST FOR KEYSTONE


================
INSTALL & UNINSTALL
================
1) install command
    $ sudo python setup.py install --record files.txt

2) call capacity command
    A RC file was created using Horizon Dashboard.
    $ source demo-openrc.sh
    $ capacity
    $ capacity capacityobj-create

2) uninstall command
    $ sudo cat files.txt | sudo xargs rm -rvf


================
COMMANDLINE TEST FOR KEYSTONE
================
Entry your new component to keystone(use commandline).

1) Create a RC file
    Create a env-rc file from Dashboard for you run keystone command.
    http://docs.openstack.org/ja/user-guide/content/cli_openrc.html

    $ source demo-openrc.sh

# Probably unused this command in minimal run.
# 2) Create user
#     Create Capacity service user.
#     $ keystone user-create --name capacity --pass %PASSWORD%
#     $ keystone user-role-add --user capacity --tenant demo --role admin

3) Create service
    Create your new component service.

    $ keystone service-create --name=<service-name> --type=<service-type> --description="<service-description>"
    ex: <service-name>        = capacity
        <service-type>        = capacityobj
        <service-description> = Capacity Service

4) Create endpoint
    Create your new component endpoint.

    $ keystone endpoint-create \
        --region RegionOne \
        --service_id=<service-id> \
        --publicurl=<service-public-url> \
        --internalurl=<service-internal-url> \
        --adminurl=<service-admin-url>

    ex: <service-id>           = your new service id from run "keystone service-list" command.
        <service-public-url>   = http://192.168.100.21:5000/v2.0
        <service-internal-url> = http://192.168.100.21:5000/v2.0
        <service-admin-url>    = http://192.168.100.21:35357/v2.0

5) Check access to your new component
    Using curl command or python-client.

    Install curl and openssl.

    $ yum install curl openssl

================
RUN TEMPEST CLI TEST
================

1) Create Config Capacity File
  Create a tempest config capacity file

  $ tox -e genconfig
  $ cp -p etc/capacityclient/capacityclient.conf.capacity etc/capacityclient/capacityclient.conf
  $ vi etc/capacityclient/capacityclient.conf
    ----------
    [DEFAULT]
    namespace = capacityclient.config

    username=demo
    tenant_name=demo
    password=pa55w0rd

    auth_url=http://<keystone-ip>:<keystone-port>/v2.0/

    admin_username=admin
    admin_tenant_name=admin
    admin_password=pa55w0rd
    ----------

  If you have permission error on tox command, you change "./build" folder, subfolder and files permission.
  ex) $ sudo chmod 777 -R ./build

2) Install Component Service
  It is necessary for you to insatall your component servies.

3) Run Tempest CLI test
  $ tox -e functional




