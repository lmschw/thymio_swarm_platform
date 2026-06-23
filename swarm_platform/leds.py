class LEDs:

    def __init__(self, connection):
        self.connection = connection

    async def top(self, r, g, b):

        await self.connection.node.set_variables({
            "leds.top": [int(r), int(g), int(b)]
        })