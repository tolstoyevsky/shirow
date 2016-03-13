from setuptools import setup

setup(name='shirow',
      version='0.1',
      description='Shirow is an implementation of a distinctive concept of a ' \
                  'remote procedure call.',
      url='https://bitbucket.org/eugulixes/shirow',
      author='CusDeb Team',
      maintainer='Evgeny Golyshev',
      maintainer_email='Evgeny Golyshev <eugulixes@gmail.com>',
      license='http://www.apache.org/licenses/LICENSE-2.0',
      packages=['shirow'],
      install_requires=[
          'tornado',
          'redis',
          'pyjwt'
      ])
