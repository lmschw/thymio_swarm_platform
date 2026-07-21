import natnet
import logging
import time

logging.basicConfig(level=logging.INFO)

client = natnet.Client.connect(
    "10.0.10.4",
    timeout=10,
)

print("Connected")


def description_callback(data):
    print("DESCRIPTION")
    print(data)


def frame_callback(rigid_bodies, markers, timing):

    for rb in rigid_bodies:
        print(
            "RB:",
            rb.id_,
            rb.position,
        )


client.set_callback(frame_callback)

print("Client attributes:")
print(dir(client))

client.spin()