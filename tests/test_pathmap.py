import nose
from nose.tools import *
from tempfile import mkdtemp
import shutil, os, sys
from os.path import join, split

#Make sure we test the local source code rather than the installed copy
test_dir = os.path.dirname(__file__)
src_dir = os.path.normpath(os.path.join(test_dir, '..'))
sys.path.insert(0, src_dir)
import pathmap

class MakeRegexRuleTest():
    
    known_results = {'.+':
                        {'hello': ['hello'], 
                         'something.txt': ['something.txt'],
                         '': pathmap.NoMatch,
                        },
                     '(.+)\.(.+)': 
                        {'something.txt': ['something.txt', 
                                           'something', 
                                           'txt'
                                          ],
                         'image_001.dcm': ['image_001.dcm',
                                           'image_001',
                                           'dcm'
                                          ],
                         'something': pathmap.NoMatch,
                        },
                     'image_([0-9]+)\.dcm': 
                        {'image_001.dcm': ['image_001.dcm', 
                                           '001'
                                          ],
                         'image_1.dcm': ['image_1.dcm',
                                         '1'
                                        ],
                         'image_one.dcm': pathmap.NoMatch,
                         'image_001.dc': pathmap.NoMatch,
                        }
                    }
                                   
    def test_known_results(self):
        for match_regex, tests in self.known_results.iteritems():
            match_rule = pathmap.make_regex_rule(match_regex)
            for input_str, results in tests.iteritems():
                assert(match_rule(input_str) == results)

class TestSimpleRules():
    paths_at_level = [['level0-dir'],
                      [join('level0-dir', 'level1-file1'), 
                       join('level0-dir', 'level1-file2'), 
                       join('level0-dir', 'level1-dir1'), 
                       join('level0-dir', 'level1-dir2'),
                      ],
                      [join('level0-dir', 'level1-dir1', 'level2-file1'),
                       join('level0-dir', 'level1-dir1', 'level2-file2'),
                       join('level0-dir', 'level1-dir1', 'level2-dir1'),
                       join('level0-dir', 'level1-dir2', 'level2-dir2'),
                       join('level0-dir', 'level1-dir2', 'level2-file3')
                      ],
                      [join('level0-dir', 'level1-dir1', 'level2-dir1', 
                            'level3-file1'),
                       join('level0-dir', 'level1-dir1', 'level2-dir1', 
                            'level3-dir1'),
                      ],
                      [join('level0-dir', 'level1-dir1', 'level2-dir1', 
                            'level3-dir1', 'level4-file1'),
                      ],
                     ]
                     
    def build_dir(self):
        for level in self.paths_at_level:
            for path in level:
                if split(path)[1].split('-')[-1].startswith('dir'):
                    os.mkdir(join(self.test_dir, path))
                else:
                    tmpfile = open(join(self.test_dir, path), 'a')
                    tmpfile.close()
    
    def setup(self):
        self.init_dir = os.getcwd()
        self.test_dir = mkdtemp()
        print self.test_dir
        self.build_dir()
        os.chdir(self.test_dir)
        
    def tearDown(self):
        os.chdir(self.init_dir)
        #shutil.rmtree(self.test_dir)
        
    def test_min_depth(self):
        for i in range(len(self.paths_at_level)):
            pm = pathmap.PathMap(depth=(i, None))
            matches = list(pm.walk('level0-dir'))
            print matches
            
            total_paths = 0
            for j in range(i, len(self.paths_at_level)):
                total_paths += len(self.paths_at_level[j])
                for path in self.paths_at_level[j]:
                    print path
                    assert(any(path == m.path for m in matches))
                    
            assert(len(matches) == total_paths)
                
    def test_max_depth(self):
        for i in range(len(self.paths_at_level)):
            pm = pathmap.PathMap(depth=(0, i))
            matches = list(pm.walk('level0-dir'))
            
            total_paths = 0
            for j in range(0, i+1):
                total_paths += len(self.paths_at_level[j])
                for path in self.paths_at_level[j]:
                    assert(any(path == m.path for m in matches))
        
            assert(len(matches) == total_paths)
        
    def test_match_regex(self):
        for i in range(len(self.paths_at_level)):
            path_map = pathmap.PathMap('level' + str(i))
            matches = path_map.get_matches('level0-dir')
            
            for j in range(i, len(self.paths_at_level)):
                for path in self.paths_at_level[j]:
                    path = os.path.normpath(path)
                    assert(['level' + str(i)] in matches)
                    
    def test_ignore_regex(self):
        path_map = pathmap.PathMap(ignore_rules=['level0'])
        matches = path_map.get_matches('level0-dir')
        assert(len(matches) == 0)
        
        for i in range(1, len(self.paths_at_level)):
            path_map = pathmap.PathMap(ignore_rules=['level' + str(i)])
            matches = path_map.get_matches('level0-dir')
            
            for j in range(0, i):
                for path in self.paths_at_level[j]:
                    path = os.path.normpath(path)
                    assert([path] in matches)

    def test_ignore_regexs(self):
        ignore_rules = ['level2-file1', '.+'+os.sep+'level3-dir1$']
        path_map = pathmap.PathMap(ignore_rules=ignore_rules)
        matches = path_map.get_matches('level0-dir')
        for match in matches:
            assert(not os.path.basename(match[0]) in ['level2-file1', 'level3-dir1'])

    def test_prune_regex(self):
        path_map = pathmap.PathMap(prune_rules=['level0-dir'])
        matches = path_map.get_matches('level0-dir')
        assert(len(matches) == 0)
        
        prune_rule = 'level2-dir1'
        path_map = pathmap.PathMap(prune_rules=[prune_rule])
        matches = path_map.get_matches('level0-dir')
        for match in matches:
            assert(match[0].find(prune_rule) == -1)
        
    def test_prune_regexs(self):
        prune_rules = ['level1-dir2', 'level3-dir1']
        path_map = pathmap.PathMap(prune_rules=prune_rules)
        matches = path_map.get_matches('level0-dir')
        for match in matches:
            for rule in prune_rules:
                assert(match[0].find(rule) == -1)
