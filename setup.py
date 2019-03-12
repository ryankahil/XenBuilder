from setuptools import setup

print("Now setting up Configuration File....")

setup(
    name="bsdxenvmbuilder",
    version='0.1',
    py_modules=['bsdxenbuilder'],
    dependency_links = ['https://github.com/xapi-project/xen-api/archive/v1.75.0.zip'],
    install_requires=[
        'Click',
        'click_configfile',
	'XenApi>=1.2'
    ],
    entry_points='''
        [console_scripts]
        bsdxenvmbuilder=bsdxenbuilder:cli
    ''',

)
