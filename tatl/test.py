"""Tests -- run with nosetests, or from command line python -mtatl.test [-u]
(The -u will update artifacts)
"""

from tatl import ExprParser, ExprSemantics, Compiler
import os, sys, json, glob
from contextlib import contextmanager
import traceback

G_TESTS = 'grammar/test.txt'
G_EXPECT = 'grammar/test.expect.json'
RULE = 'attrs'

TESTDIRS = ['tests/*.html', 'docs/slides/*.tatl']
OUT = 'tests/out/'
EXPECT = 'tests/expect/'

def test_grammar(update=0):
    parser = ExprParser.ExprParser(
        parseinfo=True,
        semantics=ExprSemantics.ExprSemantics()
    )
    if os.path.exists(G_EXPECT):
        expect = json.load(open(G_EXPECT))
    else:
        assert update, "Missing %s -- run in update mode (-u)" % EXPECT
        expect = {}
    updated = {}
    fail = 0
    for line in open(G_TESTS):
        line = line.rstrip()
        try:
            ast = parser.parse(line, rule_name=RULE)
            if hasattr(ast, 'out'):
                out = ast.out()
            else:
                out = repr(ast)
        except:
            print 'FAILURE:', line
            traceback.print_exc()
            fail += 1
        else:
            if line not in expect or expect[line] != out:
                print 'MISMATCH:',line
                print '----- got -----'
                print out
                print '---- expect ---'
                print expect.get(line, '*missing*')
                print '---------------'
                fail += 1
                updated[line] = out
            else:
                updated[line] = expect[line]
    if update and updated != expect:
        with open(G_EXPECT, 'w') as f:
            json.dump(updated, f, indent=4, sort_keys=True)
        print "Wrote", G_EXPECT
    else:
        assert not fail, "%d failures" % fail

class Case:
    def __init__(self, path):
        self.path = path
        self.file = os.path.split(path)[1]
        base = os.path.splitext(self.file)[0]
        self.outbase = os.path.join(OUT, base)
        self.expectbase = os.path.join(EXPECT, base)
        
    def read(self):
        return read(self.path)
        
    def out(self, suffix, output, compare=True, update=False):
        outf = self.outbase+suffix
        with open(outf, 'w') as f:
            f.write(output)
        if compare:
            expectf = self.expectbase+suffix
            expect = read(expectf)
            if output == expect:
                pass
            elif update:
                with open(expectf, 'w') as f:
                    f.write(output)
                print "Wrote", expectf
            else:
                raise AssertionError("%s != %s" % (outf, expectf))
        return outf

def read(filename, default=''):
    try:
        f = open(filename)
        data = f.read()
        f.close()
        return data
    except Exception, e:
        return default

def test_tatl():
    # yield our test cases so that nosetests sees them as individual cases
    if not os.path.exists(OUT): os.makedirs(OUT)
    if not os.path.exists(EXPECT): os.makedirs(EXPECT)
    for pattern in TESTDIRS:
        tests = map(Case, glob.glob(pattern))
    for test in tests:
        yield runtest, test

def runtest(test, update=False, verbose=False):
    inp = test.read()
    if verbose:
        print inp
    py = Compiler.compile(inp, test.file, out='py')
    test.out('.py', py, False)
    pyrun = runpy(py).rstrip() + '\n'
    pyout = test.out('.py.html', pyrun, True, update)
    js = Compiler.compile(inp, test.file, out='js')
    test.out('.js', js, False)
    jsrun = runjs(js).rstrip() + '\n'
    jsout = test.out('.js.html', jsrun, True, update)
    if pyrun != jsrun: 
        print "WARNING: %s and %s output should match" % (pyout, jsout)
        print "diff", pyout, jsout
        os.system("diff %s %s" % (pyout, jsout))
    if verbose: 
        print "head %s.*" % test.outbase
        
def runpy(pycode):
    try:
        d = {}
        exec pycode in d, d
        return d['html'](a='a', b=[1, 2], c=1, d={'a':'AA', 'b': [1,2,3]})
    except Exception, e:
        traceback.print_exc()
        return '<exception: %s>' % e

def runjs(jscode):
    with open('_tmp.js', 'w') as f:
        f.write(jscode+'\n\n')
        f.write('''console.log(html.call({a:'a', b:[1,2], c:1, d:{'a':'AA', 'b': [1,2,3]}}))\n''')
    return os.popen('node _tmp.js 2>&1').read()

if __name__ == '__main__':
    print "Running tests... (pass -u to update)"
    import sys
    sys.path.append('.')   # include tatlrt.py
    ExprSemantics.DEBUG = True
    update = '-u' in sys.argv
    verbose = '-v' in sys.argv
    try:
        test_grammar(update)
        for fn, test in test_tatl():
            fn(test, update, verbose)
    except Exception, e:
        traceback.print_exc()
        sys.exit(1)
