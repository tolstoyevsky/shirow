/*
 * Copyright 2018 Anton Maksimovich. All Rights Reserved.
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

import RPCClient from './client.js';

$(document).ready(function () {
    const token = $("#token").text();
    const client = new RPCClient('ws://localhost:8888/rpc/token/' + token);
    client.on('ready', function () {

        function runClick(id) {
            $("body").css("cursor", "progress");
            client.emitForce('run', id).then(
                function (message) {
                    $("body").css("cursor", "default");
                    alert(message);
                    get_images();
                    get_containers();
                });
        }

        function createImagesList(images) {
            $('#images-list').empty();
            for (const key in images) {
                $('#images-list').append("<a class='list-group-item' data-toggle='list' role='tab' id=" + key + "_" + ">" + images[key] + "<button type='button' style='float: right;' id=" + key + ">Run</button>" + "</a>");
                document.getElementById(key).addEventListener("click", function () {
                    runClick(key);
                }, false);
            }
        }

        function createContainersList(containers) {
            $('#containers-list').empty();
            $('#start').prop('disabled', true);
            $('#stop').prop('disabled', true);
            $('#remove').prop('disabled', true);
            $(".panel-heading").text('Choose docker container');
            for (const key in containers) {
                $('#containers-list').append("<a class='list-group-item' data-toggle='list' role='tab' id=" + key + ">" + key + ": " + containers[key] + "</a>");
            }

            $('#containers-list a').each(function (idx, elem) {
                if ($("#containers-pills").find(".active").text() == 'Started' && $(elem).text().includes('stopped')) {
                    $(elem).hide();
                }
                else {
                    $(elem).show();
                }
            });

            $('#containers-list a').on('click', function () {
                $(".panel-heading").text($(this).text());
                if ($(this).text().includes('stopped')) {
                    $('#start').prop('disabled', false);
                    $('#stop').prop('disabled', true);
                }
                else {
                    $('#stop').prop('disabled', false);
                    $('#start').prop('disabled', true);
                }
                $('#remove').prop('disabled', false);
            });

        }

        function get_images() {
            client.emitForce('get_images').then(createImagesList);
        }

        function get_containers() {
            client.emitForce('get_containers').then(createContainersList);
        }

        $('#start').on('click', function () {
            const id = $(".panel-heading").text().split(': ')[0];
            $("body").css("cursor", "progress");
            client.emitForce('start', id).then(function (message) {
                $("body").css("cursor", "default");
                alert(message);
                get_containers();
            });
        });


        $('#stop').on('click', function () {
            const id = $(".panel-heading").text().split(': ')[0];
            $("body").css("cursor", "progress");
            client.emitForce('stop', id).then(function (message) {
                $("body").css("cursor", "default");
                alert(message);
                get_containers();
            });
        });


        $('#remove').on('click', function () {
            const id = $(".panel-heading").text().split(': ')[0];
            $("body").css("cursor", "progress");
            client.emitForce('remove', id).then(function (message) {
                $("body").css("cursor", "default");
                alert(message);
                get_containers();
            });
        });


        $("#containers-pills a").on("click", function () {
            const $this = $(this);
            $("#containers-pills").find(".active").removeClass("active");
            $this.parent().addClass("active");

            let containers = $("#containers-list a");
            containers.each(function (idx, elem) {
                if ($this.text() == 'Started' && $(elem).text().includes('stopped')) {
                    $(elem).hide();
                }
                else {
                    $(elem).show();
                }
            });
        });

        get_images();
        get_containers();
    });
});
