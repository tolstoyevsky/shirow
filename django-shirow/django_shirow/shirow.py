# Copyright 2018 Evgeny Golyshev. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import wraps

import jwt
import redis
from django.contrib.auth.decorators import login_required
from django.conf import settings


def create_token_if_needed(func):
    """
    Tries to obtain a token from Redis. In case the try doesn't succeed, the
    decorator will create and put it into Redis and the user's session.
    """

    algorithm = getattr(settings, 'TOKEN_ALGORITHM_ENCODING', 'HS256')
    redis_host = getattr(settings, 'REDIS_HOST', '127.0.0.1')
    redis_port = getattr(settings, 'REDIS_PORT', 6379)
    token_tll = getattr(settings, 'TOKEN_TTL', 900)

    @wraps(func)
    @login_required
    def wrapper(request, *args, **kwargs):
        redis_conn = redis.StrictRedis(host=redis_host, port=redis_port, db=0)
        user_id = request.user.id
        key = 'user:{}:token'.format(user_id)
        encoded_token_from_redis = redis_conn.get(key)
        if encoded_token_from_redis:
            encoded_token = encoded_token_from_redis
        else:
            payload = {
                'user_id': user_id,
                'ip': request.META.get('REMOTE_ADDR', '127.0.0.1')
            }
            encoded_token = \
                jwt.encode(payload, settings.SECRET_KEY, algorithm=algorithm)
            redis_conn.setex(key, token_tll, encoded_token)

        request.session['token'] = encoded_token.decode('utf-8')

        return func(request, *args, **kwargs)
    return wrapper
