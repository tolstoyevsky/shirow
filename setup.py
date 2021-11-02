"""Script for building the Shirow package. """

import re
from setuptools import setup

try:
    import pypandoc
    with open('README.md', 'r', encoding='utf-8') as infile:
        LONG_DESCRIPTION = re.sub('</?p[^>]*>', '', infile.read())
        LONG_DESCRIPTION = re.sub('<img[^>]*>', '', LONG_DESCRIPTION)
        LONG_DESCRIPTION = pypandoc.convert_text(LONG_DESCRIPTION, 'rst', format='md')
except (ImportError, OSError):
    # OSError is raised when pandoc is not installed.
    LONG_DESCRIPTION = ('Shirow is an implementation of a distinctive concept of a remote '
                        'procedure call.')

with open('requirements.txt', encoding='utf-8') as outfile:
    REQUIREMENTS_LIST = outfile.read().splitlines()


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
      include_package_data=True,
      data_files=[
          ('', ['requirements.txt']),
      ],
      install_requires=REQUIREMENTS_LIST)
