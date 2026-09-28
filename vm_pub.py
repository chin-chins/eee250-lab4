"""EE 250L Lab 04 Starter Code — Fall 2026

vm_pub.py — Part 1 publisher.  Runs on your Ubuntu VM.

Every 5 seconds this program publishes three separate messages:

    <user>/vm/ip     the VM's IPv4 address, e.g. 192.168.1.42
    <user>/vm/date   today's date as YYYY-MM-DD
    <user>/vm/time   the current time as HH:MM:SS (24-hour)

Run vm_sub.py in a second terminal on your VM to watch them arrive.

    python3 vm_pub.py          # this terminal
    python3 vm_sub.py          # the other terminal

Press Ctrl-C to stop.

HOW THIS DIFFERS FROM LAB 2
---------------------------
In Lab 2 your TCP client had to know the IP address and port of the *other
program* it was talking to, and both had to be running at the same time.  Here
we only know the address of the broker.  vm_pub.py has no idea whether anybody is
subscribed to <user>/vm/ip; it publishes regardless and the broker decides where
the bytes go (nowhere, if there are no subscribers).  That decoupling - in space
AND in time - is the whole point of publish/subscribe.
"""

import socket
import time
from datetime import datetime

import paho.mqtt.client as mqtt

import config

# How often to publish, in seconds.
PUBLISH_PERIOD_S = 5

# A unique client ID.  The broker uses this to tell clients apart, and a broker
# will kick off an existing client if a NEW one connects with the SAME ID.  On a
# public broker that means (a) two students with the same ID would fight over the
# connection, and (b) your own four programs would fight with each other.  Hence
# "<user>-vm-pub", "<user>-vm-sub", and so on.
CLIENT_ID = f"{config.USERNAME}-vm-pub"


def get_vm_ip():
    """Return this VM's primary IPv4 address as a string, e.g. "192.168.1.42".

    You cannot just call socket.gethostbyname(socket.gethostname()) - on most
    Linux systems that returns 127.0.0.1, because the hostname is mapped to
    loopback in /etc/hosts.  What we actually want is "which of my interfaces
    would the kernel use to reach the outside world, and what source address
    would it stamp on the packet?"

    The standard trick is to ask the kernel that question with a UDP socket:

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()

    UDP is connectionless, so connect() here sends NO packets and needs no reply
    from 8.8.8.8 (Google's public DNS - just a well-known address that is not on
    your LAN).  All it does is make the kernel run its routing table, pick the
    outbound interface, and bind the socket to that interface's address.
    getsockname() then reads that address back out.  Nothing leaves the machine.

    Because it touches the routing table it can still fail (no network at all),
    so wrap it in try/except and fall back to "127.0.0.1" with a printed warning
    rather than crashing.  Use try/finally (or a `with` block) so the socket is
    closed either way.

    Hints:
      - socket.socket(socket.AF_INET, socket.SOCK_DGRAM) creates a UDP socket.
      - OSError is the exception family to catch.
    """
    # TODO(Part 1): find this VM's IPv4 address using the UDP-socket trick above,
    # returning "127.0.0.1" and printing a warning if it fails.
    s = None
    try: 
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      s.connect(("8.8.8.8", 80))
      ip = s.getsockname()[0]
      return ip 
    except OSError as e:
      print(f"Failed to determine IP address ({e}). Using default IP 127.0.0.1")
      return "127.0.0.1"
    finally:
      if s:
        s.close()
    


def get_date_and_time():
    """Return (date_string, time_string) for right now.

    date_string must look like "2026-09-17"  (YYYY-MM-DD)
    time_string must look like "14:05:09"    (HH:MM:SS, 24-hour)

    datetime.now() gives you a datetime object; its .strftime() method turns it
    into a string using format codes - %Y is the 4-digit year, %m the 2-digit
    month, %d the day, %H the hour on a 24-hour clock, %M minutes, %S seconds.
    `date --help` or `man strftime` lists them all.

    Note that we return two separate strings, because they go to two separate
    topics.  Deciding how finely to slice your topic tree is a real design
    question in MQTT: one topic with "2026-09-17 14:05:09" would be fewer
    messages, but then every subscriber that only cares about the date has to
    parse and discard half the payload.
    """
    # TODO(Part 1): build the two strings described above and return them as a
    # 2-tuple, e.g. return date_str, time_str
    full_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str, time_str = full_str.split(" ")
    return date_str, time_str


def on_connect(client, userdata, flags, reason_code, properties):
    """Called by paho when the broker's CONNACK packet comes back.

    A "callback" is a function you hand to a library so the library can call it
    later, when something happens.  You never call on_connect() yourself: you
    assign it to client.on_connect and paho invokes it from its network thread.
    This is a big shift from Lab 2, where your code drove everything with
    blocking recv() calls; here the library drives your code.

    paho-mqtt 2.x passes five arguments to this callback (that is what
    CallbackAPIVersion.VERSION2 means).  If you look at older tutorials online
    you will see a 4-argument version ending in `rc` - that is the 1.x API and it
    will raise a TypeError with a 2.x client, so be careful what you copy.
      client      the client object that connected
      userdata    whatever you passed as userdata= (we do not use it here)
      flags       broker-set connect flags, e.g. flags.session_present
      reason_code the result: 0 / "Success" means we are in
      properties  MQTT 5 properties; None for MQTT 3.1.1, which we are using
    """
    if reason_code == 0:
        print(f"[vm_pub] connected to {config.BROKER_HOST} (reason code {reason_code})")
    else:
        print(f"[vm_pub] CONNECTION FAILED: {reason_code}")


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    """Called when the connection drops - cleanly or otherwise.

    Worth having even in a toy program: if the broker restarts or the Wi-Fi
    blinks, you want to see it in the terminal rather than wonder why your
    subscriber went quiet.  paho's network loop reconnects on its own, and when
    it does, on_connect above runs again.
    """
    if reason_code != 0:
        print(f"[vm_pub] unexpected disconnect ({reason_code}); paho will retry")


if __name__ == "__main__":
    # paho-mqtt 2.x requires you to state which callback signature style you are
    # using.  VERSION2 is the modern one - see on_connect above.
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)

    # Attach the callbacks defined above BEFORE connecting, so that no event can
    # arrive while the client still has no handler for it.
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    print(f"[vm_pub] connecting to {config.BROKER_HOST}:{config.BROKER_PORT} as '{CLIENT_ID}' ...")

    # connect() performs the TCP handshake and sends the MQTT CONNECT packet.  We
    # spell out host=/port=/keepalive= for clarity; positional args work too.
    # The keepalive interval says how often to send a PINGREQ when there is
    # nothing else to say, so the broker can tell "idle" from "dead".
    client.connect(host=config.BROKER_HOST, port=config.BROKER_PORT,
                   keepalive=config.KEEPALIVE)

    # loop_start() asks paho to spawn a BACKGROUND THREAD that owns the socket:
    # it sends and receives packets, answers PINGREQ/PINGRESP, dispatches our
    # callbacks, and reconnects if needed.  That leaves THIS thread free to run
    # the publishing loop below.  Compare vm_sub.py, which has nothing else to do
    # and therefore uses loop_forever() to run the same machinery in the main
    # thread.  Whichever you pick, something must be running the loop - a paho
    # client with no loop is a client that never sends or receives anything.
    client.loop_start()

    # Give the background thread a moment to finish the handshake, purely so the
    # "connected" message prints before the first publish line.
    time.sleep(1)

    try:
        while True:
            ip_address = get_vm_ip()
            date_str, time_str = get_date_and_time()

            # TODO(Part 1): publish the three values on their own subtopics and
            # print one line per publish so you can see what went out.
            #
            #   config.topic("vm/ip")   -> "<user>/vm/ip"
            #   config.topic("vm/date") -> "<user>/vm/date"
            #   config.topic("vm/time") -> "<user>/vm/time"
            #
            # client.publish(<topic string>, <payload string>) is all it takes.
            # publish() returns immediately - it hands the message to the network
            # thread and does not wait for the broker.  These are QoS 0
            # ("fire and forget") messages, which is fine for a value that is
            # resent every 5 seconds anyway.
            ip_topic = config.topic("vm/ip")
            client.publish(ip_topic, ip_address)
            print(f"Published to {ip_topic}, {ip_address}")

            date_topic = config.topic("vm/date")
            client.publish(date_topic, date_str)
            print(f"Published to {date_topic}, {date_str}")

            time_topic = config.topic("vm/time")
            client.publish(time_topic, time_str)
            print(f"Published to {time_topic}, {time_str}")

            if ip_address is None or date_str is None or time_str is None:
                print("[vm_pub] TODO(Part 1) not finished yet - nothing published this round")

            time.sleep(PUBLISH_PERIOD_S)
    except KeyboardInterrupt:
        print("\n[vm_pub] Ctrl-C - shutting down")
    finally:
        # Send a clean DISCONNECT packet, THEN stop the network thread - in that
        # order, because it is the network thread that puts the packet on the
        # wire.  A clean disconnect tells the broker "I meant to leave", which
        # matters for clients that have a Last Will message registered.
        client.disconnect()
        client.loop_stop()
