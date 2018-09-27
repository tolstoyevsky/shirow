#!/usr/bin/env python3

"""
Copyright 2018 Anton Maksimovich. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os.path
import base64
import uuid

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from tornado.options import options
from tornado.log import app_log as log

from shirow.server import RPCServer, remote

import docker
from docker.errors import ImageNotFound, NotFound, DockerException


class Application(tornado.web.Application):

    """Main application class"""

    def __init__(self):
        handlers = [
            (r'/rpc/token/([\w\.]+)', RPCHandler),
        ]
        settings = dict(
            cookie_secret=base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),
            template_path=os.path.join(os.path.dirname(__file__), './'),
            static_path=os.path.join(os.path.dirname(__file__), './'),
            xsrf_cookies=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)


CLIENT = docker.from_env()


class RPCHandler(RPCServer):

    """Class for websocket RPC request handlers"""

    @remote
    def run(self, _request, image_id):
        """launch docker container from image"""

        log.info('method: run; image_id: {0}'.format(image_id))
        try:
            container = CLIENT.containers.run(image_id, detach=True)
        except ImageNotFound:
            return 'image {0} not found'.format(image_id)
        except DockerException as e:
            return 'docker error: {}'.format(e)
        return "Container {0} was successfully ran".format(container.short_id)

    @remote
    def start(self, _request, container_id):
        """start docker container"""

        log.info('method: start; container_id: {0}'.format(container_id))
        try:
            container = CLIENT.containers.get(container_id)
            container.start()
        except NotFound:
            return 'container {0} not found'.format(container_id)
        except DockerException as e:
            return 'docker error: {}'.format(e)
        return "Container {0} was successfully started".format(container_id)

    @remote
    def stop(self, _request, container_id):
        """stop docker container"""

        log.info('method: stop; container_id: {0}'.format(container_id))
        try:
            container = CLIENT.containers.get(container_id)
            container.stop()
        except NotFound:
            return 'container {0} not found'.format(container_id)
        except DockerException as e:
            return 'docker error: {}'.format(e)
        return "Container {0} was successfully stopped".format(container_id)

    @remote
    def remove(self, _request, container_id):
        """stop and remove docker container"""

        log.info('method: remove; container_id: {0}'.format(container_id))
        try:
            container = CLIENT.containers.get(container_id)
            if container.status == 'running':
                container.stop()
            container.remove()
        except NotFound:
            return 'container {0} not found'.format(container_id)
        except DockerException as e:
            return 'docker error: {}'.format(e)
        return "Container {0} was successfully deleted".format(container_id)

    @remote
    def get_images(self, _request):
        """get all docker images"""

        all_images = CLIENT.images.list()
        return {i.short_id: str(i).replace('<', '').replace('>', '') for i in all_images}

    @remote
    def get_containers(self, _request):
        """get all docker containers with status(started/stopped)"""

        started_containers = CLIENT.containers.list()
        all_containers = CLIENT.containers.list(all=True)
        return {
            c.short_id:
                ('started ({})'
                 if c in started_containers
                 else 'stopped ({})').format(str(c.image).replace('<Image: ', '').replace('>', ''))
            for c in all_containers}


def main():
    """
    Note that in this particular case the parameters specified in the
    application configuration file can be overridden by the command-line
    parameters.
    """
    tornado.options.parse_config_file(options.config_file)
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
