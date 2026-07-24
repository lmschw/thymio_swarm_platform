import csv
import datetime


async def save_robot_info_to_csv(client):
    robots = await client.list_robots()
    data = [{"hostname": hostname, "ip": robots[hostname]["ip"]} for hostname in robots.keys()]

    now = datetime.datetime.now()
    time = str(now.time()).replace(":", "")

    with open(f"thymio_ips_{now.date()}_{time}.csv", "w", newline="") as csv_file:
        fieldnames = ["hostname", "ip"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

