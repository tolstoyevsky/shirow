import tornado
from tornado.escape import json_decode, json_encode


class RPCServer(tornado.websocket.WebSocketHandler):
    def create(self):
        pass

    def destroy(self):
        pass

    # Реализаия методов, унаследованных от tornado.websocket.WebSocketHandler

    def open(self):
        self.create()

    def on_close(self):
        self.destroy()

    def on_message(self, message):
        # TODO: сделать невозможным вызовы crete, destroy и пр.

        parsed = json_decode(message)
        function_name = parsed['function_name']
        ret = {}
        try:
            method = getattr(self, function_name)
        except AttributeError:
            ret['error'] = 'the {} function is undefined'.format(function_name)
            self.write_message(json_encode(ret))
            return

        try:
            result = method(*parsed['parameters_list'])
        except TypeError:
            ret['error'] = 'number of arguments mismatch in the {} ' \
                           'function call'.format(function_name)
            self.write_message(json_encode(ret))
            return

        ret = {'result': result, 'n': parsed['n']}
        self.write_message(json_encode(ret))
