try:
    from setuptools import setup
except:
    from distutils.core import setup


def parse_requirements(requirements_filename='requirements.txt'):
    requirements = []
    with open(requirements_filename) as requirements_file:
        for requirement in requirements_file:
            requirements.append(requirement.rstrip('\n'))
    return requirements


config = dict(
    name='cloudenvy',
    version='0.3.1',
    url='https://github.com/cloudenvy/cloudenvy',
    description='Fast provisioning on openstack clouds.',
    author='Brian Waldon',
    author_email='bcwaldon@gmail.com',
    install_requires=parse_requirements(),
    packages=['cloudenvy', 'cloudenvy.commands'],
    entry_points={
        'console_scripts': [
            'envy = cloudenvy.main:main',
        ]
    },
)

setup(**config)
