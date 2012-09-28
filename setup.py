try:
    from setuptools import setup
except:
    from distutils.core import setup

config = dict(
    name='cloudenvy',
    version='0.1.0',
    url='https://github.com/bcwaldon/cloudenvy',
    description='Fast provisioning on openstack clouds.',
    author='Brian Waldon',
    author_email='bcwaldon@gmail.com',
    install_requires=['fabric', 'python-novaclient', 'pyyaml',
                      'python-glanceclient'],
    packages=['cloudenvy'],
    entry_points={
        'console_scripts': [
            'envy = cloudenvy.main:main',
        ]
    },
)

setup(**config)
