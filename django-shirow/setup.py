from setuptools import setup

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except ImportError:
    long_description = ('Django Shirow provides the create_token_if_needed '
                        'decorator which is intended for Django views. It '
                        'generates JWT (JSON Web Token) to allow clients '
                        'prove the RPC server based on Shirow that they are '
                        'authenticated.')


setup(name='django-shirow',
      version='0.3',
      description='Django Shirow package',
      long_description=long_description,
      url='https://github.com/tolstoyevsky/shirow',
      author='CusDeb Team',
      maintainer='Evgeny Golyshev',
      maintainer_email='Evgeny Golyshev <eugulixes@gmail.com>',
      license='http://www.apache.org/licenses/LICENSE-2.0',
      packages=['django_shirow'],
      install_requires=[
          'redis',
          'pyjwt'
      ])
