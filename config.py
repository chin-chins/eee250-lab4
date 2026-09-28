"""EE 250L Lab 04 Starter Code — Fall 2026

config.py - one place for the settings that every Python client in this lab shares.

Why a config file at all?  In Lab 2 you hard-coded the server's IP and port into
both the client and the server, and in Lab 3 you hard-coded the URL.  That works
for two files, but this lab has four Python programs (vm_pub.py, vm_sub.py,
vm_led.py, vm_chain.py) plus the ESP32 firmware, and they must all agree on the
broker address and on the topic prefix.  Putting those values in one module means
there is exactly one line to edit when something changes - and no chance of
vm_pub.py publishing to a topic that vm_sub.py is not listening to.

WHAT YOU MUST EDIT
------------------
1. USERNAME  -> your USC username, lowercase.  This becomes the first level of
   every topic you touch.  The public broker in Parts 1-2 is shared with the rest
   of the internet, so the prefix is what keeps your messages from colliding with
   your classmates' (and theirs from confusing you).
2. BROKER_HOST -> only in Part 3.  See the note below.

PART 3 NOTE (read this now, it explains the whole point of this file)
---------------------------------------------------------------------
In Parts 1 and 2 you use a public broker on the internet:

    BROKER_HOST = "broker.hivemq.com"        # or "broker.emqx.io" if HiveMQ is flaky

In Part 3 you run your own Mosquitto broker inside your Ubuntu VM.  The ONLY
change needed to move all four Python programs onto it is this one line:

    BROKER_HOST = "localhost"                # when the Python client runs ON the VM
    BROKER_HOST = "192.168.1.42"             # the VM's own IP, as seen by the ESP32

Use "localhost" for the Python programs that run on the VM itself, and give the
ESP32 the VM's real IPv4 address (the same address vm_pub.py publishes on
<user>/vm/ip - handy!), because "localhost" on the ESP32 would mean the ESP32.
Nothing else changes: no topic names, no callbacks, no code.  That is the payoff
of the pub/sub design - publishers and subscribers only ever name the broker.
"""

# ---------------------------------------------------------------------------
# Broker settings
# ---------------------------------------------------------------------------

# Hostname or IPv4 address of the MQTT broker.
BROKER_HOST = "localhost"

# 1883 is the standard port for unencrypted MQTT.  (8883 is MQTT over TLS, which
# we are not using - so do not type your real passwords into any topic.)
BROKER_PORT = 1883

# ---------------------------------------------------------------------------
# Your identity on the broker
# ---------------------------------------------------------------------------

# EDIT ME: replace this with your USC username (lowercase, no @usc.edu).
USERNAME = "nwamgbe"

# ---------------------------------------------------------------------------
# Keepalive
# ---------------------------------------------------------------------------
# The keepalive interval, in seconds.  If a client has nothing to say for this
# long it sends a tiny PINGREQ packet so the broker knows the TCP connection is
# still alive; if the broker hears nothing for 1.5x this interval it declares the
# client dead, drops the connection, and publishes that client's "Last Will"
# message (see vm_sub.py for why that matters for the ESP32).
KEEPALIVE = 60


def topic(suffix):
    """Return the full topic name for `suffix` under your personal namespace.

    Every topic in this lab lives under "<USERNAME>/", so instead of writing
    f"{USERNAME}/vm/ip" in four different files we write topic("vm/ip") and let
    this helper build the string.  Examples, assuming USERNAME == "ttrojan":

        topic("vm/ip")          -> "ttrojan/vm/ip"
        topic("esp32/temp")     -> "ttrojan/esp32/temp"
        topic("esp32/#")        -> "ttrojan/esp32/#"      (a wildcard subscription)
        topic("ping")           -> "ttrojan/ping"

    Note that wildcards work fine here: "#" matches this level and every level
    below it, and "+" matches exactly one level.  Wildcards are only legal in
    SUBSCRIBE, never in PUBLISH.
    """
    return f"{USERNAME}/{suffix}"


# ---------------------------------------------------------------------------
# Safety guard - do not delete this.
# ---------------------------------------------------------------------------
# Publishing to "your_usc_username/..." on a public broker would put your
# messages in the same topics as every other student who forgot to edit this
# file, which makes for a very confusing debugging session.  Rather than let that
# happen quietly, refuse to start.  SystemExit prints the message and exits with
# a non-zero status instead of dumping a traceback.
if USERNAME == "your_usc_username":
    raise SystemExit(
        "\n"
        "config.py: USERNAME is still the placeholder 'your_usc_username'.\n"
        "Open vm/config.py and set USERNAME to your USC username (lowercase),\n"
        "for example:  USERNAME = \"ttrojan\"\n"
        "Every topic in this lab is built from it, so nothing will run until you do.\n"
    )
