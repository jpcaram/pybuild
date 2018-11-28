from pathlib import Path
from subprocess import check_output, CalledProcessError
import os


class Builder(object):

    def __init__(self, *args, **kwargs):

        self.tasks = {}

        for arg in args:
            if isinstance(arg, Task):
                self.tasks[arg.name] = arg
                arg.builder = self
            else:
                raise ValueError("Not a Task: {}".format(str(arg)))

    def run(self, taskname):
        print("Builder.run('{}')".format(taskname))
        try:
            self.tasks[taskname].run()
        except IndexError:
            raise Exception('Task {} does not exist'.format(taskname))

    def get_maker(self, dep):
        """
        Finds the task that has a target that will create the dependency

        :param dep: A Dependency
        :return: A Task that has the target corresponding to the dependency
        :rtype: Task
        """

        print("Builder.get_maker({})".format(dep))

        for taskname, task in self.tasks.items():
            for target in task.targets:

                # TODO: Normalize paths before comparing.
                if isinstance(target, FileTarget) and \
                        isinstance(dep, FileDependency) and \
                        target.filepath == dep.filepath:
                    return task

        return None


class Task(object):

    def __init__(self, name, *args, **kwargs):
        self.deps = []
        self.targets = []
        self.actions = []
        self.name = name

        self.builder = None

        self.signatures = {'targets': {}, 'dependencies': {}}

        for arg in args:
            if isinstance(arg, Dependency):
                self.deps.append(arg)

            elif isinstance(arg, Target):
                self.targets.append(arg)

            elif isinstance(arg, Action):
                self.actions.append(arg)

            else:
                raise ValueError("Unsupported parameter: {}".format(str(arg)))

    def exec(self):
        """
        Runs the actions in the Task.
        """

        print("{}.exec()".format(self))

        for action in self.actions:
            action.run()

    def run(self):
        """
        Executes the task's actions and the dependencies actions
        when the task or its dependencies are out-of-date.

        :return: True if this task's actions were executed
        """

        print("{}.run()".format(self))

        for dep in self.deps:

            maker = self.builder.get_maker(dep)
            if maker:
                print("   {}.run(): {} makes {}".format(self, maker, dep))
                maker.run()

            # Failed to create the dependency. There was either no maker,
            # or the maker failed to create it.
            if not dep.exists():
                raise DependencyError(dep)

        if not self.local_uptodate():
            self.exec()
            return True

        print("   {}.run(): Did not execute.".format(self))
        return False

    def uptodate(self) -> bool:
        """
        Recursive up-to-date check. Descends into Tasks that
        make the dependencies of this Task.

        :return: True is globally up to date.
        :rtype: bool
        """
        print("{}.uptodate()".format(self))

        # Locally up to date?
        if not self.local_uptodate():
            print("   {}.uptodate(): Locally out of date. -> False".format(self))
            return False
        print("   {}.uptodate(): Locally up to date.".format(self))

        # All dependencies up to date?
        for dep in self.deps:
            maker = self.builder.get_maker(dep)
            if not maker.uptodate():
                return False
        print("   {}.uptodate(): All dependencies up-to-date.".format(self))

        return True

    def local_uptodate(self) -> bool:
        """
        Checks that this task is up to date only with respect
        to itself. For a global check see Task.uptodate()

        :return: True is up to date.
        :rtype: bool
        """

        print("{}.local_uptodate()".format(self))

        for dep in self.deps:

            signature = dep.get_signature()
            try:
                old_signature = self.signatures['dependencies'][dep]
                if signature != old_signature:
                    print("   {}.local_uptodate(): Signature of {} has changed".format(self, dep))
                    return False
            except KeyError:
                # No old signature, it is new
                print("   {}.local_uptodate(): Did not have a signature for {}".format(self, dep))
                return False

            print("   {}.local_uptodate(): Signature of {} has not changed".format(self, dep))

        print("   {}.local_uptodate(): All signatures are old.".format(self))

        return self.all_targets_exist()

    def all_targets_exist(self):
        print("{}.all_targets_exist()".format(self))
        return all([t.exists() for t in self.targets])

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __repr__(self):
        return "Task('{}')".format(self.name)


class TSTask(Task):
    """
    Timestamp-based task. The up-to-date definition is based on the relative
    timestamp of targets and dependencies. This type of Task should mimic the
    bahvior of GNU Make.

    The only difference with its parent is the local_uptodate() method.
    """

    def local_uptodate(self) -> bool:
        """
        Compares the timestamps of targets and dependencies.
        If all dependencies are older that all targets, the it is up-to-date.
        Otherwise, including if any target is missing, then it is not up-to-date.

        :return: Whether is is up to date.
        :rtype: bool
        """

        # If any target is missing, False.
        if not self.all_targets_exist():
            print("{}.local_uptodate(): A target is missing.".format(self))
            return False

        # We compare the 'signature' returned by the target/dependency.
        # We are assuming for now that it is a timestamp (integer).
        tgttstamps = [target.get_signature() for target in self.targets]
        deptstamps = [dep.get_signature() for dep in self.deps]

        # No dep. stamps -> no deps. All good. True.
        if len(deptstamps) == 0:
            return True

        # At least one dependency is newer than a target.
        if max(deptstamps) >= min(tgttstamps):
            print("{}.local_uptodate(): A dependency is newer than a target.".format(self))
            return False

        return True


class Action(object):

    def run(self):
        raise NotImplemented('Action.run() must be overriden in subclass.')


class CmdAction(Action):

    def __init__(self, cmd):
        self.cmd = cmd
        self.error = None
        self.output = None

    def run(self):
        print("{}.run()".format(self))

        self.error = None
        self.output = None

        try:
            self.output = check_output(self.cmd, shell=True)
        except CalledProcessError as e:
            self.error = e
            raise ActionError(e)

    def __repr__(self):
        return "CmdAction('{}')".format(self.cmd)


class ActionError(Exception):
    pass


class Dependency(object):

    def exists(self):
        return False

    def __hash__(self):
        raise NotImplemented('Dependecy Class must be subclassed.')

    def __eq__(self, other):
        raise NotImplemented('Dependecy Class must be subclassed.')

    def get_signature(self):
        raise NotImplemented('Dependecy Class must be subclassed.')


class FileDependency(Dependency):

    def __init__(self, filepath):

        self.filepath = filepath

    def __hash__(self):
        return hash(self.filepath)

    def __eq__(self, other):
        return self.filepath == other.filepath

    def get_signature(self):
        return os.path.getmtime(self.filepath)

    def exists(self):
        return Path(self.filepath).is_file()

    def __repr__(self):
        return "FileDependency('{}')".format(self.filepath)


class DependencyError(Exception):
    pass


class Target(object):

    def exists(self):

        # Default behavior?
        return True

    def __hash__(self):
        raise NotImplemented('Target Class must be subclassed.')

    def __eq__(self, other):
        raise NotImplemented('Target Class must be subclassed.')


class FileTarget(Target):

    def __init__(self, filepath):

        self.filepath = filepath

    def exists(self):

        return Path(self.filepath).is_file()

    def __hash__(self):
        return hash(self.filepath)

    def __eq__(self, other):
        return self.filepath == other.filepath

    def get_signature(self):
        return os.path.getmtime(self.filepath)

    def __repr__(self):
        return "FileTarget('{}')".format(self.filepath)
