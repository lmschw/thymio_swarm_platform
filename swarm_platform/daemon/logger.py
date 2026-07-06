import csv


class SessionLogger:
    def __init__(self, path):
        self.file = open(path, "w", newline="")
        self.writer = csv.writer(self.file)
        self.header = None

    def log(self, state, command):
        row = {}

        row.update(state)
        row.update(command)

        if self.header is None:
            self.header = list(row.keys())
            self.writer.writerow(self.header)

        self.writer.writerow(
            [row[k] for k in self.header]
        )

        self.file.flush()

    def close(self):
        self.file.close()