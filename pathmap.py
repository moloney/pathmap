'''Module for parsing directory structures.'''

import os, re, warnings
from operator import attrgetter
from os.path import normpath
from itertools import izip
from collections import namedtuple
import scandir


try:
    basestring
except NameError:
    basestring = str # Python3
    

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class NoMatchType(object):
    '''Singleton that can be returned by rules to indicate they did not match
    the given input.'''
    __metaclass__ = Singleton

    def __nonzero__(self):
        return False

    __bool__ = __nonzero__

NoMatch = NoMatchType()

def make_regex_rule(regex_str):
    '''Takes a string containing a regex pattern and returns a function
    that can be used as a PathMap rule.

    The returned 'match_info' will be a list containing the full regex match
    plus any matched subgroups.
    '''
    regex = re.compile(regex_str)
    def rule(path, dir_entry):
        result = regex.search(path)
        if result:
            return [result.group()] + list(result.groups())
        return NoMatch

    return rule


def default_match_rule(path, dir_entry):
    '''Matches anything and returns None as the 'match_info'.'''
    return None


def warn_on_error(oserror):
    '''The default callback function for scandir errors. Raises a
    warning.

    Can be overridden with any function that takes a single argument
    (the OSError exception).'''
    warnings.warn('Error on listdir: ' + str(oserror))


MatchResult = namedtuple('MatchResult', 'path dir_entry match_info')
'''The return value from PathMap.walk. Contains the full path, the
scandir.DirEntry object, and the return value from the match rule.'''


class PathMap(object):
    '''Object which contains a number of 'rules' that define how it will
    traverse a directory structure and what paths it will yield. The onject 
    can then be used to generate matches starting from one or more root paths.

    Each 'rule' is a callable takes two arguments, the full path and the
    corresponding scandir.DirEntry object. Any rule can also be provided as
    a string, in which case it will be converted to a callable using
    `make_regex_rule`.

    Parameters
    ----------
    match_rule : callable
        Returns the 'match_info' result or `NoMatch` if the path should be
        ignored. If None the `default_match_rule` will be used.

    ignore_rules : list of callable
        If any of these callables return a value that evaluates to True the
        path will be ignored. The first rule that returns True will cause all
        subsequent `ignore_rules` and the `match_rule` to be skipped.

    prune_rules : list of callable
        If a path is a directory and any of these callables return a value
        that evaluates to True the directory will not be descended into. The
        directory path itself may still be matched.

    depth : tuple or int
        The minimum and maximum depth for recursion. If an single int is
        given only paths at that depth will be generated.

    sort : bool
        If true the paths in each directory will be processed and generated
        in sorted order, with directories proceeding files.

    on_error : callable
        Callback for errors from scandir. The errors are typically due to a
        directory being deleted between being found and being recursed into.

    follow_symlinks : bool
        Follow symbolic links. If set to True it is possible to get stuck in
        an infinite loop.

    '''
    def __init__(self, match_rule=None, ignore_rules=None, prune_rules=None,
                 depth=(0,None), sort=False, on_error=None,
                 follow_symlinks=False):

        if match_rule is None:
            match_rule = default_match_rule
        self.match_rule = match_rule
        if ignore_rules:
            self.ignore_rules = ignore_rules[:]
        else:
            self.ignore_rules = []
        if prune_rules:
            self.prune_rules = prune_rules[:]
        else:
            self.prune_rules = []
        if not isinstance(depth, tuple):
            depth = (depth, depth)
        if depth[0] < 0:
            raise ValueError("The minimum depth must be positive")
        if not depth[1] is None and depth[1] < depth[0]:
            raise ValueError("The maximum depth must be None or greater than "
                             "the minimum")
        self.depth = depth
        self.sort = sort
        self.on_error = on_error
        self.follow_symlinks = follow_symlinks

    def _convert_regex_rules(self):
        if isinstance(self.match_rule, basestring):
            self.match_rule = make_regex_rule(self.match_rule)
        for index, rule in enumerate(self.ignore_rules):
            if isinstance(rule, basestring):
                self.ignore_rules[index] = make_regex_rule(rule)
        for index, rule in enumerate(self.prune_rules):
            if isinstance(rule, basestring):
                self.prune_rules[index] = make_regex_rule(rule)

    def _test_target_path(self, path, dir_entry):
        for rule in self.ignore_rules:
            if bool(rule(path, dir_entry)) == True:
                return NoMatch
        result = self.match_rule(path, dir_entry)
        return result

    def matches(self, root_paths, dir_entries=None):
        '''Generate matches by recursively walking from the 'root_paths' down
        into the directory structure.

        The object's rules define which paths are generated, and the
        `match_rule` provides the `match_info` result as it's return value.

        Parameters
        ----------
        root_paths : iter
            Provides the paths to start our walk from. If you want these to
            be processed into sorted order you must sort them yourself.

        dir_entries : iter or None
            If given, must provide a scandir.DirEntry for each root path. If
            not provided we must call stat for each root path.

        Returns
        -------
        result : MatchResult
            A `MatchResult` object is generated for each matched path.
        '''
        # Allow a single path or an iterable to be passed
        if isinstance(root_paths, basestring):
            root_paths = [root_paths]
            if dir_entries is not None:
                dir_entries = [dir_entries]

        # Make sure any regex rules have been converted to a callable
        self._convert_regex_rules()

        # Crawl through each root path
        for root_idx, root_path in enumerate(root_paths):
            # Get rid of any extra path seperators
            root_path = normpath(root_path)

            #Get the corresponding DirEntry
            if dir_entries is None:
                p, name = os.path.split(root_path)
                if p == '':
                    p = '.'
                root_entry = scandir.GenericDirEntry(p, name)
            else:
                root_entry = dir_entries[root_idx]

            # Check if the root path itself is matched
            if self.depth[0] == 0:
                match_info = self._test_target_path(root_path, root_entry)
                if not match_info is NoMatch:
                    yield MatchResult(root_path, root_entry, match_info)
                if not root_entry.is_dir():
                    continue

            # Check if the root_path is pruned
            prune_root = False
            for rule in self.prune_rules:
                if rule(root_path, root_entry):
                    prune_root = True
                    break
            if prune_root:
                continue

            # Walk through directory structure checking paths against
            # rules
            curr_dir = (root_path, root_entry)
            next_dirs = []
            while True:
                # Determine the current depth from the root_path
                curr_depth = (curr_dir[0].count(os.sep) -
                              root_path.count(os.sep)) + 1
                              
                #Build a list of entries for this level so we can sort if 
                #requested
                curr_entries = []
            
                # Try getting the contents of the current directory
                try:
                    for e in scandir.scandir(curr_dir[0]):
                        # Keep directories under the depth limit so we can 
                        # resurse into them
                        if e.is_dir():
                            if (self.depth[1] is not None and
                                curr_depth > self.depth[1]
                               ):
                                continue
                        else:
                            # Plain files can be ignored if they violate 
                            # either depth limit
                            if (curr_depth < self.depth[0] or 
                                (self.depth[1] is not None and
                                 curr_depth > self.depth[1])
                               ):
                                continue
                            
                        #Add to the list of entries for the curr_dir
                        curr_entries.append(e)
                            
                except OSError as error:
                    #Handle errors from the scandir call
                    if self.on_error is not None:
                        self.on_error(error)
                    else:
                        raise
                else:                
                    # Sort the entries if requested
                    if self.sort:
                        curr_entries.sort(key=attrgetter('name'))

                    # Iterate through the entries, yielding them if they are a 
                    # match
                    for e in curr_entries:
                        p = os.path.join(curr_dir[0], e.name)
                        
                        if e.is_dir():
                            # If it is not pruned, add it to next_dirs. Only
                            # follow symlinks if requested.
                            if self.follow_symlinks or not e.is_symlink():
                                for rule in self.prune_rules:
                                    if rule(p, e):
                                        break
                                else:
                                    next_dirs.append((p, e))
                                    
                            # If we are below min depth we don't try matching 
                            # the dir
                            if curr_depth < self.depth[0]:
                                continue
                        
                        # Test the path against the match/ignore rules
                        match_info = self._test_target_path(p, e)
                        if not match_info is NoMatch:
                            yield MatchResult(p, e, match_info)

                # Update curr_dir or break if we are done
                try:
                    curr_dir = next_dirs.pop(0)
                except IndexError:
                    break

