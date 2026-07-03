from swarm_platform.projects.manager import ProjectManager

pm = ProjectManager("example_project")

print(pm.list_experiments())

cls = pm.experiment("light_leds_green")

print(cls.name)
print(cls)