try:
    from setuptools import setup
except:
    from distutils.core import setup

import os


def parse_requirements(requirements_filename='requirements.txt'):
    requirements = []
    if os.path.exists(requirements_filename):
        with open(requirements_filename) as requirements_file:
            for requirement in requirements_file:
                requirements.append(requirement)
    return requirements

config = dict(
    name='cloudenvy',
    version='0.1.0',
    url='https://github.com/bcwaldon/cloudenvy',
    description='Fast provisioning on openstack clouds.',
    author='Brian Waldon',
    author_email='bcwaldon@gmail.com',
    install_requires=parse_requirements(),
    packages=['cloudenvy'],
    entry_points={
        'console_scripts': [
            'envy = cloudenvy.main:main',
        ]
    },
)

setup(**config)
