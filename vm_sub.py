"""EE 250L Lab 04 Starter Code — Fall 2026

vm_sub.py — Part 1 + Part 2 subscriber.  Runs on your Ubuntu VM.

This is the one window you keep open all lab: it listens to everything your VM
and your ESP32 publish under <user>/vm/ and <user>/esp32/ and prints it, so you
can see at a glance whether vm_pub.py, the ESP32, and vm_led.py are all doing
what you think they are.  (The Part 3 chain topics, <user>/ping and <user>/pong,
sit outside both of those prefixes; vm_chain.py subscribes to them itself.)

In Part 1 it subscribes to the three topics vm_pub.py publishes, one
subscribe() call each:

    <user>/vm/ip   <user>/vm/date   <user>/vm/time                (Part 1)

In Part 2 the ESP32 adds six more topics, so instead of six more subscribe()
calls you use a topic WILDCARD (explained below) to cover them all at once:

    <user>/esp32/#   everything the ESP32 publishes            (Part 2)

Either way, CUSTOM CALLBACKS are registered for four specific topics and the
default on_message() catches the rest.

    python3 vm_sub.py

Press Ctrl-C to stop.

TOPIC WILDCARDS (Part 2)
------------------------
A wildcard is a pattern in a SUBSCRIBE that matches many topics at once.
"#" is the multi-level wildcard: "ttrojan/esp32/#" matches ttrojan/esp32/temp,
ttrojan/esp32/led/state, and anything else below ttrojan/esp32.  "+" is the
single-level wildcard: "ttrojan/+/ip" would match ttrojan/vm/ip and
ttrojan/esp32/ip but not ttrojan/a/b/ip.  Wildcards are legal only in SUBSCRIBE;
you must always PUBLISH to a concrete topic.  Try it from the command line:
mosquitto_sub -h broker.hivemq.com -t "ttrojan/#" -v shows everything you own.

TWO THINGS THAT WILL LOOK LIKE MAGIC IN PART 2
----------------------------------------------
1. LAST WILL AND TESTAMENT.  You will see "<user>/esp32/status = offline" appear
   without the ESP32 sending anything - because it cannot, that is the point.
   The ESP32 registers a "last will" message when it connects: topic
   <user>/esp32/status, payload "offline", retained, QoS 1.  The BROKER holds
   onto it and publishes it on the ESP32's behalf if the ESP32 disappears without
   a clean DISCONNECT (unplugged, crashed, out of Wi-Fi range).  That takes up to
   about 1.5 x keepalive = ~90 s with our 60 s keepalive, so be patient when you
   demo it.  If the ESP32 disconnects cleanly the will is discarded instead -
   a clean goodbye is not a death.  This is how MQTT gives you liveness
   monitoring for free; in Lab 2 you would have had to build a heartbeat and a
   timeout yourself.

2. RETAINED MESSAGES.  <user>/esp32/status = "online" and
   <user>/esp32/led/state are published with the RETAIN flag set, which tells the
   broker to keep the last such message and hand it to every NEW subscriber the
   instant it subscribes.  So when you start vm_sub.py you should immediately see
   the current LED state and the ESP32's status even though nothing was published
   just then - and you will see them again every time you restart vm_sub.py.
   Without retain, a subscriber learns nothing until the next publish happens.
   (Normal telemetry like /temp is NOT retained: a five-minute-old temperature
   would be misleading.)
"""

import paho.mqtt.client as mqtt

import config

# See vm_pub.py for why each program gets its own client ID.
CLIENT_ID = f"{config.USERNAME}-vm-sub"


# ---------------------------------------------------------------------------
# Custom message callbacks
# ---------------------------------------------------------------------------
# paho lets you register a handler for a specific topic (or topic filter) with
# client.message_callback_add(topic, function).  When a message arrives, paho
# checks the registered filters first and calls the most specific match; only if
# nothing matches does it fall through to client.on_message.  That saves you from
# writing one giant if/elif chain on msg.topic inside on_message - the same idea
# as routing by URL in Flask in Lab 3, where @app.route("/temp") beat parsing the
# path yourself.
#
# All message callbacks take the same three arguments:
#   client    the client object
#   userdata  whatever you passed as userdata= (unused here)
#   msg       an MQTTMessage with .topic (str), .payload (BYTES), .qos, .retain
#
# .payload is bytes, not str, because MQTT payloads are arbitrary binary.  Ours
# are UTF-8 text, so decode them: msg.payload.decode().  Print a DIFFERENT prefix
# in each callback - during the demo that is how you (and the interviewer) can
# tell which callback actually ran.


def on_vm_ip(client, userdata, msg):
    """Handles <user>/vm/ip - the VM's IP address, from vm_pub.py."""
    # TODO(Part 1): print the payload with the prefix "[custom: VM IP]"
    payload = msg.payload.decode()
    print(f"[custom: VM IP] : {payload}")
    return 


def on_vm_date(client, userdata, msg):
    """Handles <user>/vm/date - today's date, from vm_pub.py."""
    # TODO(Part 1): print the payload with the prefix "[custom: VM date]"
    payload = msg.payload.decode()
    print(f"[custom: VM date] : {payload}")
    return


def on_esp32_temp(client, userdata, msg):
    """Handles <user>/esp32/temp - the ESP32's internal die temperature, in C.

    Note this is the temperature of the chip itself, not the room: it reads
    high, and it climbs while the radio is busy.  That is expected.
    """
    # TODO(Part 2): print the payload with the prefix "[custom: ESP32 temp]"
    payload = msg.payload.decode()
    print(f"[custom: ESP32 temp]: {payload}")
    return 


def on_esp32_status(client, userdata, msg):
    """Handles <user>/esp32/status - "online" (retained) or "offline" (the LWT).

    Reminder from the module docstring: "offline" here was published by the
    BROKER, not by the ESP32, from the Last Will and Testament the ESP32
    registered when it connected.  msg.retain is True when the broker is
    replaying a retained message to you because you just subscribed, and False
    when it is live - printing it makes the difference visible.
    """
    # TODO(Part 2): print the payload with the prefix "[custom: ESP32 status]"
    payload = msg.payload.decode() 
    print(f"[custom: ESP32 status]: {payload}")
    return 


# ---------------------------------------------------------------------------
# Default message callback
# ---------------------------------------------------------------------------

def on_message(client, userdata, msg):
    """The catch-all handler for subscribed topics with no custom callback.

    Functions are objects in Python, which is why we can assign this one to
    client.on_message below.  Anything you subscribed to (the vm/ topics or <user>/esp32/#)
    that is not claimed by a message_callback_add() filter lands here: in this
    lab that means <user>/vm/time, <user>/esp32/ip, /rssi, /uptime, /button,
    <user>/esp32/led/state, and also <user>/esp32/led itself - the command
    vm_led.py sends to the ESP32 is under our wildcard too, so you see both the
    request and the ESP32's echo.  Keeping a default handler around is good
    practice - it is how you notice a topic you forgot about, or a typo in a
    topic name.
    """
    # TODO(Part 1): print the topic AND the payload, in this format:
    #   [default] topic=<user>/vm/time payload=14:05:09
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"[default] topic={topic} payload={payload}")
    return

def on_connect(client, userdata, flags, reason_code, properties):
    """Called when the broker's CONNACK arrives.  Do your subscribing HERE.

    Why subscribe inside on_connect() rather than in main after connect()?
    Two reasons.  First, a SUBSCRIBE packet is only valid on an established
    session, and right after connect() the handshake may not be finished.
    Second and more importantly: subscriptions live in the broker's memory for
    the duration of a session, so if the connection drops and paho reconnects for
    us, the new session starts with NO subscriptions.  Because on_connect runs
    again on every (re)connect, putting the subscribe calls here means they are
    automatically renewed and your subscriber silently keeps working.  Put them
    in main and your program would appear to be running fine while receiving
    nothing at all.

    See vm_pub.py's on_connect for what the five parameters mean.
    """
    if reason_code != 0:
        print(f"[vm_sub] CONNECTION FAILED: {reason_code}")
        return

    print(f"[vm_sub] connected to {config.BROKER_HOST} (reason code {reason_code})")

    # TODO(Part 1): subscribe to the three topics vm_pub.py publishes, one call
    # each:  client.subscribe(config.topic("vm/ip"))  and likewise for "vm/date"
    # and "vm/time".
    ip = config.topic("vm/ip")
    date = config.topic("vm/date")
    time = config.topic("vm/time")

    client.subscribe(ip)
    print(f"Subscribed to {ip}")

    client.subscribe(date)
    print(f"Subscribed to {date}")

    client.subscribe(time)
    print(f"Subscribed to {time}")
    # TODO(Part 2): also subscribe to everything the ESP32 publishes.  It has six
    # topics, so use the multi-level wildcard instead of six calls:
    #   client.subscribe(config.topic("esp32/#"))
    # Print a line saying what you subscribed to - during the demo it is good
    # evidence that this step happened.
    esp32 = config.topic("esp32/#")
    client.subscribe(esp32)
    print(f"Subscribed to {esp32}")

    # TODO(Part 1): register the custom callbacks for the VM topics with
    #   client.message_callback_add(<topic>, <function name, no parentheses>)
    # for config.topic("vm/ip") -> on_vm_ip and config.topic("vm/date") -> on_vm_date.
    client.message_callback_add(ip, on_vm_ip)
    client.message_callback_add(date, on_vm_date)
    # time doesn't have a callback bc/ there's no function for it 
   
    # TODO(Part 2): do the same for config.topic("esp32/temp") -> on_esp32_temp
    # and config.topic("esp32/status") -> on_esp32_status.
    temp = config.topic("esp32/temp")
    status = config.topic("esp32/status")
    client.message_callback_add(temp, on_esp32_temp)
    client.message_callback_add(status, on_esp32_status)

    # Registering them here (alongside the subscribe calls) keeps the whole
    # routing table in one place; message_callback_add is idempotent, so calling
    # it again on a reconnect simply replaces the same entry.


if __name__ == "__main__":
    # paho-mqtt 2.x: state the callback API version explicitly.  See vm_pub.py.
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)

    # Attach the default message handler and the connect handler.  Note we assign
    # the function OBJECTS - no parentheses, because we are not calling them.
    client.on_message = on_message
    client.on_connect = on_connect

    print(f"[vm_sub] connecting to {config.BROKER_HOST}:{config.BROKER_PORT} as '{CLIENT_ID}' ...")
    client.connect(host=config.BROKER_HOST, port=config.BROKER_PORT,
                   keepalive=config.KEEPALIVE)

    try:
        # In Lab 2 your programs drove the network themselves: you called recv()
        # and blocked until bytes showed up.  Here the library does that for you,
        # but something still has to run its loop.  vm_pub.py needed its main
        # thread for the publishing loop, so it used loop_start() to put paho's
        # loop on a background thread.  This program has nothing else to do, so
        # we hand the main thread to paho with loop_forever(): it blocks here
        # (essentially forever), processing socket traffic, sending keepalive
        # pings, dispatching the callbacks above, and reconnecting if the
        # connection is lost.  Everything interesting from now on happens inside
        # a callback.
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[vm_sub] Ctrl-C - shutting down")
        client.disconnect()
