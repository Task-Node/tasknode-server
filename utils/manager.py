import sys


class Command:
    def __init__(self, name, func):
        self.name = name
        self.func = func


class Manager:
    def __init__(self):
        self.commands = []

    def command(self, f):
        self.commands.append(Command(f.__name__, f))

    def list_commands(self):
        return sorted(map(lambda x: x.name, self.commands))

    def get_command(self, name):
        return next(filter(lambda x: x.name == name, self.commands), None)

    def run(self):
        arg1 = sys.argv[1]
        command = self.get_command(arg1)
        if command:
            command.func()
        else:
            print(f'Command must be one of [{", ".join(self.list_commands())}]')
