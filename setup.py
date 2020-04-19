"""Script for building the Shirow package. """

import re
from setuptools import setup

try:
    import pypandoc
    with open('README.md', 'r') as infile:
        LONG_DESCRIPTION = re.sub('</?p[^>]*>', '', infile.read())
        LONG_DESCRIPTION = re.sub('<img[^>]*>', '', LONG_DESCRIPTION)
        LONG_DESCRIPTION = pypandoc.convert_text(LONG_DESCRIPTION, 'rst', format='md')
except ImportError:
    LONG_DESCRIPTION = ('Shirow is an implementation of a distinctive concept of a remote '
                        'procedure call.')


setup(name='shirow',
      version='0.4',
      description='Shirow package',
      long_description=LONG_DESCRIPTION,
      url='https://github.com/tolstoyevsky/shirow',
      author='CusDeb Team',
      maintainer='Evgeny Golyshev',
      maintainer_email='Evgeny Golyshev <eugulixes@gmail.com>',
      license='http://www.apache.org/licenses/LICENSE-2.0',
      packages=['shirow'],
      install_requires=[
          'tornado==4.5.3',
          'redis',
          'pyjwt'
      ])
