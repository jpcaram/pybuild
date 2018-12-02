# pybuild
Python library for creating make-like build systems.

This project is in a very early stage of development. Some things work, some don't. If you want to be part of the
early specification and idea-generation phase, see the Wiki, message me, create a pull request with ideas, etc.

With this said, the purpose of this
project is to provide reusable code (a library) that can be used to create tools that can execute a "build" mechanism
like GNU Make, however, being more powerful, flexible, and independent from any command line implementation.

The implementation is object-oriented, and its use is minimalist, clean, and extensible.

Example:

```python
from pybuild import *

builder = Builder(

    TSTask("task1",
           CmdAction("wc -l file2.txt > file1.txt"),
           FileTarget("file1.txt"),
           FileDependency("file2.txt")
           ),

    TSTask("task2",
           CmdAction('echo "Hello World!" > file2.txt'),
           FileTarget("file2.txt"),
           )
)

builder.run('task1')
```
