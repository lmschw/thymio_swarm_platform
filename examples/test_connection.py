from swarm_platform.thymio import Thymio

robot = Thymio()

robot.connect()

print(robot.read_variables("prox.horizontal"))

robot.close()