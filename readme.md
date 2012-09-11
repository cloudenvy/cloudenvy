# Cloud Envy

The goal of CloudEnvy is to allow developers to easily spin up instances
for development in an OpenStack cloud.

It should be usable on Rackspace Cloud, HP Cloud, or wherever the
OpenStack APIs are in place.

NOTE: Currently CloudEnvy only works for a single instance, we are
looking to expand into multi-tenant multi-instance environments, but for
the prototype 1 environment == 1 instance.

## Installation

Use setup.py to install cloudenvy and the dependencies:

python setup.py install

## Configuration

You must set options in ~/.cloudenvy.  Here is a minimal config:

    [cloud:envy]
    keypair_name=xxx
    keypair_location=/home/anthony/.ssh/id_rsa.pub
    image_name=Ubuntu 11.10 cloudimg amd64
    flavor_name=m1.small
    assign_floating_ip=True
    os_username=xxx
    os_password=xxx
    os_tenant_name=xxx
    os_auth_url=http://127.0.0.1:5000/v2.0

    [template:envy]
    # Image name to use for new instance
    image_name=Ubuntu 11.10 cloudimg amd64
    assign_floating_ip=True

Specify an alternative config with the environment variable CLOUDENV_CONFIG.

## Usage

Launching a development environment couldn't be easier.

Set up and launch a bare instance.

    envy up

Start an instance with verbose logging.

    envy -v up

To name or switch your environment something other than the default, you must pass in
a fabric argument for the ENV_NAME

    envy up:<name>

Deploy anything you need on the instance. NOTE: This defaults to
./userdata in the same directory as your fabfile.

    envy provision

Or, 

    envy provision -u [file]

Backup your instance with an image snapshot.

    envy backup

Get your instance IP address

    envy ip

SSH into your instance (note that you will have to allow port 22 in the default security group)

    envy ssh

Destroy your instance

    envy destroy
