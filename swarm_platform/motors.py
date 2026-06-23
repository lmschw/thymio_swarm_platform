class Motors:

    def __init__(self, connection):
        self.connection = connection

    async def drive(self, left, right):

        await self.connection.node.set_variables({
            "motor.left.target": [int(left)],
            "motor.right.target": [int(right)],
        })

    async def stop(self):
        await self.drive(0, 0)