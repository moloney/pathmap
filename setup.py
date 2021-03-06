from setuptools import setup

setup(name='pathmap',
      version='2.0b1',
      description='Directory Structure Parsing Module',
      author='Brendan Moloney',
      author_email='moloney@ohsu.edu',
      install_requires=['scandir>=0.9'],
      extras_require = {'test': ["nose"]},
      py_modules=['pathmap'],
      test_suite = 'nose.collector'
     )
