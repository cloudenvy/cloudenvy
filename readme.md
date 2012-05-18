# Cloud Envy

The goal of CloudEnvy is to allow developers to easily spin up instances
for development in an OpenStack cloud.

It should be usable on Rackspace Cloud, HP Cloud, or wherever the
OpenStack APIs are in place.

NOTE: Currently CloudEnvy only works for a single instance, we are
looking to expand into multi-tenant multi-instance environments, but for
the prototype 1 environment == 1 instance.

## Usage

Launching a development environment couldn't be easier.

Required OpenStack Environment Variables (make sure you use your own
account!)

    export OS_AUTH_URL=http://10.9.9.9:5000/v2.0
    export OS_TENANT_ID=7c1fcbd408cb437092b418c54e0faQe1
    export OS_TENANT_NAME=russia
    export OS_USERNAME=brosefstalin
    export OS_PASSWORD=iliketurtles

Setup and launch a bare instance.

    fab up  

To name or switch your environment something other than the default, you must pass in
a fabric argument for the ENV_NAME

    fab up:<name>

Deploy anything you need on the instance. NOTE: This defaults to
./userdata in the same directory as your fabfile.

    fab provision

Backup your instance with an image snapshot.

    fab backup

Get your instance IP address

    fab ip

SSH into your instance

    fab ssh

Destroy your instance

    fab destroy

