import tornado
from tornado.escape import json_decode, json_encode


class RPCServer(tornado.websocket.WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        tornado.websocket.WebSocketHandler.__init__(self, application, request,
                                                    **kwargs)
        self.remote_functions = []
        for method in dir(self):
            if method.endswith('__remote'):
                self.remote_functions.append(method)

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
        ret = {}
        parsed = json_decode(message)
        function_name = parsed['function_name'] + '__remote'
        if (function_name in dir(self)) and \
           (function_name in self.remote_functions):
            method = getattr(self, function_name)
        else:
            ret['error'] = 'the {} function is ' \
                           'undefined'.format(parsed['function_name'])
            self.write_message(json_encode(ret))
            return

        try:
            result = method(*parsed['parameters_list'])
        except TypeError:
            ret['error'] = 'number of arguments mismatch in the {} ' \
                           'function call'.format(parsed['function_name'])
            self.write_message(json_encode(ret))
            return

        ret = {'result': result, 'n': parsed['n']}
        self.write_message(json_encode(ret))
