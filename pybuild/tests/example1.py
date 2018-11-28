from pybuild import *
import shutil
import os

# try:
#     os.remove('./file1.txt')
# except FileNotFoundError:
#     pass

try:
    os.remove('./file2.txt')
except FileNotFoundError:
    pass


builder = Builder(
    TSTask("task1",
           CmdAction("wc -l file2.txt > file1.txt"),
           FileTarget("file1.txt"),
           FileDependency("file2.txt")
           ),

    TSTask("task2",
           #CmdAction('cat "Hello World!" > file2'),
           #CmdAction('echo "Hello World!" > file2'),
           CmdAction('echo "Hello World!" > file2.txt'),
           FileTarget("file2.txt"),
           )
)

builder.run('task1')
