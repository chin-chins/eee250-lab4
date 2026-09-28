"""EE 250L Lab 04 Starter Code — Fall 2026

vm_chain.py — Part 3 ping/pong counter chain.  Runs on your Ubuntu VM.

    python3 vm_chain.py            # start the chain at 0
    python3 vm_chain.py 42         # start the chain at 42

Press Ctrl-C to stop.

THE GAME
--------
    VM  ---- <user>/ping  n   ---->  ESP32
    VM  <--- <user>/pong  n+1 -----  ESP32
    VM  ---- <user>/ping  n+2 ---->  ESP32        (after a 1 s pause)
    ...forever

This program publishes the starting integer on <user>/ping and subscribes to
<user>/pong.  The ESP32 does the mirror image: it subscribes to <user>/ping and,
whenever a number arrives, publishes that number plus one on <user>/pong.  Each
time a pong comes back here we add one again, wait a second so the numbers are
readable, and send the next ping.  The counter should climb 0, 2, 4, 6, ... in
this terminal and 1, 3, 5, ... on the ESP32's serial monitor.

By Part 3 the broker is Mosquitto running inside your own VM, so the only thing
that changed from Part 2 is BROKER_HOST in config.py.  Nothing in this file cares
which broker it is talking to.

WHY THIS IS A GOOD DEBUGGING TOOL
---------------------------------
There is no timeout and no retry here: if the chain stops climbing, exactly one
link is broken, and the last number printed tells you which side dropped the
ball.  An even number was the last thing you sent means the ESP32 never answered;
an odd number means the ESP32 answered and your subscription or callback is the
problem.  (A real system would add a timeout and resend - worth thinking about
for the interview: what would you change to make this chain self-healing?)
"""

import argparse
import time

import paho.mqtt.client as mqtt

import config

CLIENT_ID = f"{config.USERNAME}-vm-chain"

# How long to pause before answering a pong, in seconds.  Without it the two
# devices would spin as fast as the network allows and you would see a blur of
# numbers scroll past (and give the broker a pointless hammering).
CHAIN_DELAY_S = 1


def on_pong(client, userdata, msg):
    """Custom callback for <user>/pong - the ESP32's reply.

    ABOUT THE 1-SECOND SLEEP
    ------------------------
    This callback runs on paho's network thread, the same thread that reads the
    socket, dispatches callbacks, and answers keepalive pings.  So a
    time.sleep(CHAIN_DELAY_S) in here does not just delay our reply: it freezes
    ALL of this client's MQTT traffic for that second.  Any message that arrives
    meanwhile waits in the OS socket buffer until we return.

    For this lab that is completely fine - the chain is strictly one message at a
    time, our keepalive is 60 s, and a 1 s stall is nowhere near that.  (The Sp26
    version of this lab suggested exactly this time.sleep(1) so the numbers are
    readable.)  But recognise the pattern, because it is the classic way to
    wreck a real event-driven program: a callback that blocks for 30 s, or that
    waits on an HTTP request, will silently stall every other callback and can
    make the broker declare your client dead when the keepalive is missed.  The
    grown-up fix is to hand the slow work to another thread or a queue and return
    from the callback immediately.

    WHAT TO DO HERE
    ---------------
      1. msg.payload is bytes; decode it and cast it to int.
      2. Add 1.
      3. Print what you received and what you are about to send - this print IS
         the demo, so make it readable.
      4. time.sleep(CHAIN_DELAY_S).
      5. Publish the new number (as a STRING - MQTT payloads are bytes, and
         client.publish() will not accept a bare int) on config.topic("ping").

    A note on robustness: int() raises ValueError on a payload that is not a
    number.  On a public broker that is a real possibility; on your own VM broker
    it means you published something odd by hand.  Wrapping the cast in
    try/except and printing a complaint is optional here but good habit - an
    exception raised inside a paho callback is caught and logged by the library,
    so it will not crash your program, but it will silently break the chain.
    """
    # TODO(Part 3): implement steps 1-5 above.
    try:
      num = int(msg.payload.decode())
      new_num = num + 1
      print(f"Received: {num}, Sending {new_num}")
      time.sleep(CHAIN_DELAY_S)
      client.publish(config.topic("ping"), str(new_num))
    except ValueError:
      print(f"Received non-integer payload: {msg.payload}") 


def on_connect(client, userdata, flags, reason_code, properties):
    """Called when the broker's CONNACK arrives.

    `userdata` is the starting integer: we passed it to mqtt.Client(userdata=...)
    in main below, and paho hands it back to every callback.  It is a convenient
    way to give callbacks some context without reaching for a global variable.

    Note that on_connect runs again after any automatic reconnect, which means
    the starting ping would be sent again and you would briefly have two numbers
    circulating.  That is acceptable for a lab demo; think about how you would
    avoid it (a flag? clean_session? a sequence number in the payload?).
    """
    if reason_code != 0:
        print(f"[vm_chain] CONNECTION FAILED: {reason_code}")
        return

    print(f"[vm_chain] connected to {config.BROKER_HOST} (reason code {reason_code})")

    # TODO(Part 3): subscribe to config.topic("pong") and register on_pong as its
    # custom callback with client.message_callback_add().  Do it HERE, inside
    # on_connect, so the subscription is re-created automatically if the
    # connection drops and paho reconnects - see vm_sub.py for the full
    # explanation.
    client.subscribe(config.topic("pong"))
    client.message_callback_add(config.topic("pong"), on_pong)

    # TODO(Part 3): kick the chain off by publishing the starting value - it is
    # in `userdata` - to config.topic("ping").  Remember to str() it, and print a
    # line saying what you sent.  Subscribe FIRST and publish SECOND: if the
    # ESP32 answers instantly, a subscription that is not in place yet means the
    # pong is delivered to nobody and the chain never starts.
    client.publish(config.topic("ping"), str(userdata))
    print(f"Published {userdata} to the broker")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Start an MQTT ping/pong counter chain with the ESP32.",
        epilog="example:  python3 vm_chain.py 0",
    )
    parser.add_argument("start_int", nargs="?", type=int, default=0,
                        help="integer to start the chain at (default: 0)")
    args = parser.parse_args()

    # userdata= is paho's way of attaching your own object to the client; every
    # callback receives it as its second argument.
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID,
                         userdata=args.start_int)
    client.on_connect = on_connect

    print(f"[vm_chain] connecting to {config.BROKER_HOST}:{config.BROKER_PORT} as '{CLIENT_ID}' ...")
    client.connect(host=config.BROKER_HOST, port=config.BROKER_PORT,
                   keepalive=config.KEEPALIVE)

    try:
        # Like vm_sub.py, this program has nothing to do in its main thread - all
        # the work happens in on_pong - so we give the main thread to paho.
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[vm_chain] Ctrl-C - shutting down")
        client.disconnect()
