/*
 * Copyright 2021 Denis Gavrilyuk <karpa4o4@gmail.com>
 * Copyright 2016 Maxim Karpinskiy <karpinski20@gmail.com>
 * Copyright 2016 Evgeny Golyshev <eugulixes@gmail.com>
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

import {EventEmitter} from 'events'
import {HostValidationError} from './errors'
import {Callback, MessageData, ResultCache} from './types'
import {diagnoseConnection, isWsHost, log} from './utils'

const RETRIES_COUNT = 5

/**
 * Creates a connection with an RPC-server and acts as an RPC-client, allowing remote procedures
 * to be called.
 */
export const Shirow = (wsHost: string) => {
    let attempt = 1
    let client: WebSocket
    let isOpened = false
    let doNotReconnect = false
    let isDiagnosed = false
    let callNumber = 0
    let queue: string[] = []
    const resultCache: ResultCache = {}

    if (!isWsHost(wsHost)) {
        throw new HostValidationError()
    }

    const messageEmitter = new EventEmitter()
    const errorEmitter = new EventEmitter()
    _connect()

    return {
        disconnect,
        emit,
        emitForce,
    }

    // Private methods

    function _connect () {
        client = new WebSocket(wsHost)

        client.onopen = () => {
            log('connection is established')
            attempt = 1
            isOpened = true

            queue.forEach(_send)
            queue = []
        }

        client.onclose = () => {
            isOpened = false

            if (doNotReconnect) {
                log('connection closed')
                return
            }

            /*
             * The WebSocket API doesn't provide any way to get response headers. Thus, at the first
             * attempt to reconnect to the RPC server we have to send a simple HTTP GET request
             * in order to diagnose a problem.
             *
             * The diagnosing has been made before and the current token is valid, but after
             * a while connection was broken.
             */
            if (attempt === 1 && !isDiagnosed) {
                diagnoseConnection(wsHost)
                    .then(() => {
                        isDiagnosed = true
                        _reconnect()
                    })
                    .catch(() => {
                        log('Authorization attempt failed')
                    })
            } else {
                _reconnect()
            }
        }

        client.onmessage = (event) => {
            const data = JSON.parse(event.data) as MessageData
            const strMarker = String(data.marker)

            if (typeof data.result !== 'undefined') {
                messageEmitter.emit(strMarker, data.result)
            } else {
                errorEmitter.emit(strMarker, data.error)
            }

            if (data.eod === 1) {
                messageEmitter.removeAllListeners(strMarker)
                errorEmitter.removeAllListeners(strMarker)
            }
        }
    }

    function _reconnect () {
        if (attempt < RETRIES_COUNT) {
            const delay = attempt * attempt
            log(`retry connection after ${delay} seconds`)

            setTimeout(_connect, delay * 1000)
            attempt++
        } else {
            log(`connection failed after ${RETRIES_COUNT} retries`)
        }
    }

    function _send (data: string) {
        if (isOpened) {
            client.send(data)
        } else {
            queue.push(data)
        }
    }

    function _emit (procedureName: string, force: boolean, ...parametersList: any[]) {
        /*
         * The Shirow client and server use so called markers to map a remote
         * procedure call with its return value. To call a remote procedure,
         * the Shirow client sends to the Shirow server the name of the procedure, a
         * list of its input parameters and the marker associated with it. When
         * the procedure is ready to return a result, the server sends to the
         * client the return value and the marker. Then, using the marker, the
         * client is able to call the corresponding handler function. The call
         * number is used as a marker.
         */
        const data = {
            function_name: procedureName,
            parameters_list: parametersList,
            marker: callNumber++,
        }
        const jsonData = JSON.stringify(data)

        const cacheKey = `${data.function_name}${JSON.stringify(data.parameters_list)}`
        const strMarker = String(data.marker)

        // When force is set to true we don't cache the result.
        if (force) {
            _send(jsonData)
        } else {
            const cachedValue = resultCache[cacheKey]
            if (cachedValue) {
                setTimeout(() => {
                    messageEmitter.emit(strMarker, cachedValue)
                })
            } else {
                _send(jsonData)
            }
        }

        return {
            then: function (cb: Callback) {
                messageEmitter.on(strMarker, (result) => {
                    if (!force) {
                        resultCache[cacheKey] = result
                    }
                    cb(result)
                })
                return this
            },
            catch: function (cb: Callback) {
                errorEmitter.on(strMarker, cb)
                return this
            },
        }
    }

    // Public methods

    /**
     * Closes the connection without trying to reconnect.
     */
    function disconnect () {
        doNotReconnect = true
        client.close()
    }

    /**
     * Calls the remote procedure. Caches the result of the call and uses the cached call result
     * (if the procedure was called before).
     */
    function emit (procedureName: string, ...parametersList: any[]) {
        return _emit(procedureName, false, ...parametersList)
    }

    /**
     * Calls the remote procedure. Doesn't cache the result of the call and doesn't use
     * the cached call result.
     */
    function emitForce (procedureName: string, ...parametersList: any[]) {
        return _emit(procedureName, true, ...parametersList)
    }
}

export default Shirow
