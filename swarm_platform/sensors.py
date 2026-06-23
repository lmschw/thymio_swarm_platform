class Sensors:

    def __init__(self, connection):

        self.connection = connection

    async def proximity(self):

        return list(
            self.connection.node["prox.horizontal"]
        )