[![pypi](https://img.shields.io/pypi/v/django-shirow.svg)](https://pypi.org/project/django-shirow/)

# Django Shirow

To connect to the RPC servers based on [Shirow](https://github.com/tolstoyevsky/shirow), clients have to be authenticated using the [Django authentication system](https://docs.djangoproject.com/en/2.0/topics/auth/). Thus, the package provides the `create_token_if_needed` decorator which is intended for Django views. First, the decorator tries to obtain a token from Redis. Then, in case the try doesn't succeed, `create_token_if_needed` will create and put it into Redis and the user's session. Finally, the client can get the token from the session and prove the RPC server he/she is an authenticated user.

The decorator uses JWT for generating tokens. JWT (JSON Web Token) is the open standard defined in [RFC 7519](https://tools.ietf.org/html/rfc7519).

## Installation

```
$ pip install django-shirow
```

## Usage

This Django application uses the following configuration keys:

* `SECRET_KEY` is a string which contains a secret. Django uses the configuration key for [cryptographic signing](https://docs.djangoproject.com/en/2.0/topics/signing/), but `create_token_if_needed` uses it for signing the tokens, using the algorithm specified by `TOKEN_ALGORITHM_ENCODING` (see below).
* `TOKEN_TTL` is a number which contains a time-in-seconds value. It indicates how long tokens are considered valid. If `TOKEN_TTL` is not set, then TTL is set to `900` (15 minutes).
* `TOKEN_ALGORITHM_ENCODING` is a string which contains [one of the algorithms](https://pyjwt.readthedocs.io/en/latest/algorithms.html#digital-signature-algorithms) used for signing tokens. If `TOKEN_ALGORITHM_ENCODING` is not set, then the algorithm is set to `HS256`.
* `REDIS_HOST` is a string which contains the Redis host. If `REDIS_HOST` is not set, then the host is set to `127.0.0.1`.
* `REDIS_PORT` is a number which contains the port the Redis server listens on. If `REDIS_PORT` is not set, then the port is set to `6379`.
