[![pypi](https://img.shields.io/pypi/v/shirow.svg)](https://pypi.org/project/shirow/)

# Shirow

<p align="center">
    <img src="/logo/400x232.png" alt="Shirow">
</p>

Shirow is an RPC server framework based on top of [Tornado](http://tornadoweb.org/en/stable/). It relies on the WebSocket protocol for transport and uses JSON-messages as payload.

The primary goal of Shirow is to simplify creating microservices using Tornado, allowing clients to leverage some of the Django facilities such as the [Django authentication system](https://docs.djangoproject.com/en/2.2/topics/auth/). Thus, Shirow might help with the task of creating (micro)services which require the clients to be authenticated via the Django authentication system.

The project was named after Masamune Shirow, a mangaka who is best known for such mangas as [Black Magic](https://en.wikipedia.org/wiki/Black_Magic_(manga)), [Appleseed](https://en.wikipedia.org/wiki/Appleseed_(manga)) and [Ghost in the Shell](https://en.wikipedia.org/wiki/Ghost_in_the_Shell_(manga)).

## Features

* Each (micro)service built using Shirow is an RPC server that relies on the WebSocket protocol for transport and uses JSON-messages as payload.
* Shirow expands the [Tornado implementation of the WebSocket protocol](https://www.tornadoweb.org/en/stable/websocket.html) with an JWT-based authentication layer. So, a client has to pass a valid JWT token to the RPC server, which was received after a successful authentication procedure, to prove Shirow that it's an authenticated.
* Shirow is fully compatible with the JWT tokens provided by [Simple JWT](https://github.com/SimpleJWT/django-rest-framework-simplejwt), a JSON Web Token authentication plugin for the Django REST Framework. The main requirement to JWT tokens is they must contain the following fields:
  * `user_id`: the id of the user the the request was sent on behalf of;
  * `exp`: the expiration time stored as an absolute Unix timestamp.
* The clients can be written in JavaScript using the Shirow NPM package.

## Authors

See [AUTHORS](AUTHORS.md).

## Licensing

Shirow is available under the [Apache License, Version 2.0](LICENSE).
