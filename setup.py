from setuptools import setup

setup(name='pathmap',
      version='2.0a2',
      description='Directory Structure Parsing Module',
      author='Brendan Moloney',
      author_email='moloney@ohsu.edu',
      install_requires=['scandir'],
      extras_require = {'test': ["nose"]},
      py_modules=['pathmap'],
      test_suite = 'nose.collector'
     )
