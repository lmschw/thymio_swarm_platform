class Sensors:

    def __init__(self, connection):
        self.connection = connection

    async def proximity(self):

        self.connection.client.process_waiting_messages()

        return list(
            self.connection.node["prox.horizontal"]
        )