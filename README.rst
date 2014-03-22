.. -*- rest -*-
.. vim:syntax=rest

=======
pathmap
=======

This package provides similar functionality to the Unix `find` command, but 
in a much more pythonic fashion. A `PathMap` object encapsulates a number of 
rules that define how to traverse a directory structure and try to match the 
paths along the way. The `PathMap.walk` method takes one or more root paths 
to start from and generates a `MatchResult` object for any path it encounters 
that match its rules.

The package is built upon the `scandir` package which provides effiecient 
directroy listing and the ability to avoid unneeded 'stat' calls on the paths 
being generated.


Running Tests
-------------

You can run the tests with:

$ python setup.py test

Or if you already have the *nose* package installed you can use the 
*nosetests* command in the top level directory:

$ nosetests

Installing
----------

You can install the *.zip* or *.tar.gz* package with the *easy_install* 
or *pip* commands.

Or you can uncompress the package and in the top level directory run:

$ python setup.py install
