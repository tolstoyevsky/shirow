
## Shirow Django demo
Shirow Django demo project with front(django) and back(shirow) sides. It shows django-shirow token auth system. Primary functionality is docker containers control system.

### Requirements
 - Python 3
 - NPM
 - Redis (configure host and port in shirow.conf, default localhost:6379)

### Install and run

``` bash
$ git clone https://github.com/tolstoyevsky/shirow.git
$ cd shirow/django-shirow/django_shirow_demo/front
$ npm install
$ npm run demo
$ cd ..
$ pip3 install -r requirements.txt
$ cd back
$ python3 demo.py
$ cd ../front
$ python3 manage.py runserver
```

Link for browser: [http://localhost:8000/](http://localhost:8000/)

If you don`t have a Django user, create them from [Django-admin](http://localhost:8000/admin) panel(but first you need to [create](https://docs.djangoproject.com/en/2.1/intro/tutorial02/#creating-an-admin-user) a superuser)