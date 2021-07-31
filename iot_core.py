#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import time
import os
import json
import re
import logging

from config import *

from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder, iotshadow

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO if not DEBUG else logging.DEBUG)


# TODO:  understand this
io.init_logging(getattr(io.LogLevel, io.LogLevel.Info.name), 'stderr')


# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    logger.error(f"Connection interrupted. error: {error}")


# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    logger.info(f"Connection resumed. return_code: {return_code} session_present: {session_present}")

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        logger.warning("Session did not persist. Resubscribing to existing topics...")
        resubscribe_future, _ = connection.resubscribe_existing_topics()

        # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
        # evaluate result with a callback instead.
        resubscribe_future.add_done_callback(on_resubscribe_complete)


def change_shadow_value(thing_name, values):

    print("Updating reported shadow value to '{}'...".format(values))
    request = iotshadow.UpdateShadowRequest(
        thing_name=thing_name,
        state=iotshadow.ShadowState(
            reported=values
        )
    )
    future = shadow_client.publish_update_shadow(request, mqtt.QoS.AT_LEAST_ONCE)
    future.result()

    logger.info("Update request published.")



# Spin up resources
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=MQTT_HOST,
        cert_filepath=AWS_CERT_PATH,
        pri_key_filepath=AWS_KEY_PATH,
        client_bootstrap=client_bootstrap,
        ca_filepath=AWS_ROOT_CA,
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed,
        client_id=AWS_CLIENT_ID,
        clean_session=False,
        keep_alive_secs=6)


logger.info(f"Connecting to {MQTT_HOST} with client ID '{AWS_CLIENT_ID}'...")

connect_future = mqtt_connection.connect()

# Future.result() waits until a result is available
connect_future.result()
logger.info("Connected!")



