# cloudenvy

The goal of cloudenvy is to allow developers to easily spin up instances
for development in an OpenStack cloud.

cloudenvy is built on a few principles.

    1. Bootstrapping an environment should only take 1 command.
    2. Hardware is the enemy, virtualize your environments so others can play with you.
    3. Never rely on tools which you can not hack.

## Installation

Use setup.py to install cloudenvy and the dependencies:

    python setup.py install

## Configuration

### User Config
You must set your user options in ~/.cloudenvy.yml. User options include a few general preferences, and your cloud credentials. Here is a minimal config:

    cloudenvy:
      clouds:
        cloud01:
          os_username: username
          os_password: password
          os_tenant_name: tenant_name
          os_auth_url: http://keystone.example.com:5000/v2.0/

          # Optional
          #os_region_name: RegionOne

### Project Config

Much like Vagrant, each Envy must have a corresponding configuration file in the project working directory. We call this file Envyfile. It should be located at `Envyfile.yml` the root of your project.

    project_config:
      name: foo
      image: Ubuntu 12.04 cloudimg amd64

      # Optional
      #remote_user: ubuntu
      #flavor_name: m1.small
      #auto_provision: False
      provision_scripts:
        #- provision_script.sh

NOTE: For the `image` property you can use either an image name or an id. If you use a development cloud where ids change frequently its probably better to use the image name, in all other cases we recommend you use an image id... but it is your call.

## Usage

### Launch

Launch a bare instance

    envy up

NOTE: If your Envyfile contains the `provision_scripts` config option, envy up will automatically run `envy provision` when your Envy has finished booting. If you do not want to auto provision your Envy you must pass the `--no-provision` flag like so:

    envy up --no-provision

NOTE: If your Envyfile contains the `files` config option, envy will automatically run `envy files` when your Envy has finished booting, before `envy provision` is run. If you do not want to automatically put your files on the new instance, you must pass the `--no-files` flag:

    envy up --no-files

NOTE: Use the ```-v``` flag to get verbose logging output. Example: ```envy -v up```

NOTE: CloudEnvy sets certain metadata (such as `os_auth_url`) on the instance at launch time to make provisioning and other post-launch tasks more developer-friendly.

### Files

Files can be placed onto the new instance. The files work with a ``files`` hash in your Envyfile.

    #...
    files:
      README.md: '~'

The key of the hash is the local path relative to your Envyfile, or absolute, and the value is the remote location. Files and directories are accepted, according to the same restrictions as Fabric's put directive.

To invoke the file uploads directly you can run:

    envy files

If your remote machine doesn't have sudo installed, and since cloudenvy uses sudo
when pushing files to your remote machine, you can optionnaly turn the use of
sudo off by using `files_use_sudo: False`. 

    #...
    files_use_sudo: False
    files:
      README.md: '~'

### Provision

To provision a script, you must set the path to one or more shell scripts (in the future these can be any type of excecutable files).

    envy provision

If you are attempting to debug provision scripts, you can pass in several scripts, which will be run in order, like so:

    envy provision --scripts ~/Desktop/scripts/foo.sh ~/Desktop/scripts/bar.sh

NOTE: Provisioning an Envy does not use the ```OpenStack CloudConfigDrive```. Instead it uploads the provision script, and runs it using Fabric. This allows you to perform operations which require ssh authentication (such as a git clone from a private repository)


### Get your Envy IP

    envy ip

### SSH to your Envy

SSH into your instance.

    envy ssh


NOTE: It is highly recommended that you enable SSH Agent Forwarding. The fastest way to do this is to run:

    ssh-add


### Run a command on your Envy

    envy run "ls ~/foo"

### Destroy your Envy

Destroy your instance

    envy destroy

## Advanced cloudenvy

#### Name your Envys

If desired you can launch multiple Envys for a single project. This is useful if you want to run an Envy for development, and a separate Envy for testing. Your Envy name will always be prefaced for the project it belongs to, to do this run:

    envy up -n foo #this will result in ProjectName-foo

NOTE: If you choose to do this, you will need to pass the `-n` flag into all of your commands, for example if you want to ssh into the Envy created above you would have to run:

    envy ssh -n foo

You will quickly lose track of all of the Envys for your project, so we added a command that will allow you to retrieve each Envy name in context of your proejct. To do this run:

    envy list

NOTE: This will likely change, as cloudenvy gets smarter in how it tracks instances, for example we should probably be using server metadata to track if an instance is from cloudenvy.

#### Passing in your user configuration (dotfiles)

You can pass in basic dotfiles by running:

    envy dotfiles

This defaults to uploading the following files `.vimrc, .gitconfig, .gitignore, .screenrc`. If you would like to pass in a custom set of dotfiles, you can specify them like so

    envy dotfiles -f '.vimrc, .gitconfig'

NOTE: The custom dotfiles must be in a comma separated list, and all of them in a single set of quotes.

#### Simple file uploading

You can upload files to your Envy via SFTP by running:

    envy scp ~/cat-photo.jpg ~/ZOMGKITTY.jpg

#### Defining custom security groups

By default cloudenvy opens ports `22, 443, 80, 8080, 5000, and 9292`. These ports are generally useful for OpenStack development, but if you have other requirements, or just don't like to have empty open ports you can define them in your Envyfile

To add custom security groups you can put define them in your Envyfile following the format below:

      sec_groups: [
        'icmp, -1, -1, 0.0.0.0/0',
        'tcp, 22, 22, 0.0.0.0/0',
        'tcp, 80, 80, 0.0.0.0/0',
        'tcp, 3000, 3000, 0.0.0.0/0'
      ]

#### Useful patterns for provision scripts

There are a number of common parameters that need to be configured on a per-instance basis during provisioning, many of which aren't obviously available. However, much of this data can be obtained from the cloud metadata service (a concept originated by Amazon's EC2 and extended by OpenStack). The metadata service is a RESTful web service which lives at a known IP address (169.254.169.254) which is routable from each instance in the cloud.

Here are some commonly needed pieces of data and the corresponding bash code to get them from the core metadata service:

Instance UUID:

    curl http://169.254.169.254/openstack/latest/meta_data.json | python -c 'import sys, json; print json.load(sys.stdin)["uuid"]'

Instance Name:

    curl http://169.254.169.254/openstack/latest/meta_data.json | python -c 'import sys, json; print json.load(sys.stdin)["name"]'

Fixed IP:

    curl http://169.254.169.254/latest/meta-data/local-ipv4

Floating IP:

    curl http://169.254.169.254/latest/meta-data/public-ipv4

The user-defined server metadata is also available via an OpenStack extension to the metadata service which returns a JSON blob:

OpenStack Auth URL (added to server metadata by CloudEnvy):

    curl http://169.254.169.254/openstack/latest/meta_data.json | python -c 'import sys, json; print json.load(sys.stdin)["meta"]["os_auth_url"]'

Arbitrary Instance Metadata Values (be sure to specify the key you want):

    curl http://169.254.169.254/openstack/latest/meta_data.json | python -c 'import sys, json; print json.load(sys.stdin)["meta"][sys.argv[1]]' <your key here>

Name of first public key:

    curl http://169.254.169.254/openstack/latest/meta_data.json | python -c 'import sys, json; print json.load(sys.stdin)["public_keys"].keys()[0]'
