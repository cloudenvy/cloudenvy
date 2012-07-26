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

You can set options in ~/.cloudenvy instead of passing environment
variables. This config file also has additional options such as:

    keypair_name=xxx
    keypair_location=/Users/xxx/.ssh/id_rsa.pub
    image_name=Ubuntu 11.10 cloudimg amd64
    flavor_name=m1.large
    assign_floating_ip=True

## Usage

Launching a development environment couldn't be easier.

Required OpenStack Environment Variables (make sure you use your own
account!)

    export OS_AUTH_URL=http://10.9.9.9:5000/v2.0
    export OS_TENANT_ID=7c1fcbd408cb437092b418c54e0faQe1
    export OS_TENANT_NAME=russia
    export OS_USERNAME=brosefstalin
    export OS_PASSWORD=iliketurtles

Set up and launch a bare instance.

    envy up

To name or switch your environment something other than the default, you must pass in
a fabric argument for the ENV_NAME

    envy up:<name>

Deploy anything you need on the instance. NOTE: This defaults to
./userdata in the same directory as your fabfile.

    envy provision

Backup your instance with an image snapshot.

    envy backup

Get your instance IP address

    envy ip

SSH into your instance (note that you will have to allow port 22 in the default security group)

    envy ssh

Destroy your instance

    envy destroy

