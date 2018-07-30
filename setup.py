import re
from setuptools import setup

try:
    import pypandoc
    with open('README.md', 'r') as f:
        long_description = re.sub('</?p[^>]*>', '', f.read())
        long_description = re.sub('<img[^>]*>', '', long_description)
        long_description = pypandoc.convert_text(long_description, 'rst',
                                                 format='md')
except ImportError:
    long_description = ('Shirow is an implementation of a distinctive concept '
                        'of a remote procedure call.')


setup(name='shirow',
      version='0.3',
      description='Shirow package',
      long_description=long_description,
      url='https://github.com/tolstoyevsky/shirow',
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
