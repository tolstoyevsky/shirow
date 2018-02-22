[![pypi](https://img.shields.io/pypi/v/shirow.svg)](https://pypi.org/project/shirow/)

# Shirow

<p align="center">
    <img src="/logo/400x232.png" alt="Shirow">
</p>

Shirow is an RPC server framework based on top of [Tornado](http://tornadoweb.org/en/stable/). It relies on the WebSocket protocol for transport and uses JSON-messages as payload.

The project was named after Masamune Shirow, a mangaka who is best known for such mangas as [Black Magic](https://en.wikipedia.org/wiki/Black_Magic_(manga)), [Appleseed](https://en.wikipedia.org/wiki/Appleseed_(manga)) and [Ghost in the Shell](https://en.wikipedia.org/wiki/Ghost_in_the_Shell_(manga)).

## Features

The primary goal of Shirow is to simplify creating microservices using Tornado, allowing clients to leverage some Django facilities. Thus, Shirow expands the Tornado implementation of the WebSocket protocol with an authentication layer, so that clients have to be authenticated using the [Django authentication system](https://docs.djangoproject.com/en/2.0/topics/auth/) to connect to the RPC server. The client has to pass a valid token to the RPC server, which was received after a successful authentication procedure, to prove Shirow that it's an authenticated. See the [create_token_if_needed](https://github.com/tolstoyevsky/shirow/tree/master/django-shirow) decorator to learn how to make Django views create the tokens.

## Authors

See [AUTHORS](AUTHORS.md).

## Licensing

Shirow is available under the [Apache License, Version 2.0](LICENSE).
