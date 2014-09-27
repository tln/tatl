"""Tests -- run with nosetests, or from command line python -mtatl.test [-u]
(The -u will update artifacts)
"""

from tatl import ExprParser, ExprSemantics, Compiler, front_matter
import os, sys, json, glob
from contextlib import contextmanager
import traceback, cStringIO
import tatlrt

G_TESTS = 'grammar/test.txt'
G_EXPECT = 'grammar/test.expect.json'
RULE = 'attrs'

TESTDIRS = ['tests/*.html', 'docs/examples/*.html']
OUT = 'tests/out/'
EXPECT = 'tests/expect/'
EXCLUDE = 'tests/skip.txt'

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
            import pdb
            pdb.post_mortem()
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

    def out(self, suffix, output, compare=None, update=False):
        if isinstance(output, str):
            # wtf
            try:
                output = output.decode('ascii')
            except:
                # wtf*2
                print self.path, suffix, 'Bogus data!'
                raise
        outf = self.outbase+suffix
        with open(outf, 'w') as f:
            f.write(output.encode('utf8'))
        if compare:
            expectf = self.expectbase+suffix
            expect = read(expectf).decode('utf8')
            if output == expect:
                pass
            elif update:
                with open(expectf, 'w') as f:
                    f.write(output.encode('utf8'))
                print "Wrote", expectf
            else:
                return compare(outf, expectf)
        return outf

    def front_matter(self):
        try:
            return front_matter(self.path)
        except:
            print "WARNING: front matter failed", self.path
            return {}

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
    try:
        with open(EXCLUDE) as f:
            exclude = set(f.read().splitlines())
    except:
        exclude = set()
    tests = []
    for pattern in TESTDIRS:
        tests += [Case(f) for f in glob.glob(pattern) if f not in exclude]
    runtest = Runner(False).runtest
    for test in tests:
        yield runtest, test

class Runner:
    def __init__(self, update):
        self.update = update

    def log(self, *args):
        pass

    def skipped(self, test):
        self.log('Skipped:', test.file)
        return True

    def start(self, test):
        self.log('----', test.path)

    def warn(self, text):
        if text in self.expected_warnings:
            if self.expected_warnings.index(text) > 0:
                self.log('Warning out of order:', text)
            self.expected_warnings.remove(text)
        else:
            self.log('Unexpected warning:', text)

    def runpy_failed(self, test, py):
        print "Error running", test.path
        raise

    def runtest(self, test):
        self.start(test)

        fm = test.front_matter()
        if fm.get('test') == 'skip':
            return self.skipped(test)
        self.expected_warnings = fm.get('expect', {}).get('warn', [])

        inp = test.read()
        self.log(inp)
        pyrun = jsrun = None

        py = None
        try:
            py = Compiler.compile(inp, test.path, out='py', warn=self.warn)
            pyc = compile(py, test.file, 'exec')
        except:
            if py:
                print py
            self.compile_fail(inp, test, 'py')
        else:
            self.log('--py:\n', py)
            c = test.out('.py', py, False)
            tatlrt.use_fast(False)
            try:
                pyrun = runpy(py).rstrip() + '\n'
            except:
                pyrun = self.runpy_failed(test, py)
            pyout = test.out('.py.html', pyrun, self.compare, self.update)
            self.log('->', c)

            if tatlrt.use_fast(True):
                self.log("checking fast")
                try:
                    pyfrun = runpy(py).rstrip() + '\n'
                except:
                    pyfrun = self.runpy_failed(test, py)
                pyfout = test.out('.fast.py.html', pyfrun, self.compare, self.update)
                if pyfrun != pyrun:
                    self.run_mismatch(pyfout, pyout)
            else:
                self.log('Could not use fast module')
                import pdb
                pdb.set_trace()
                print 'fast->', tatlrt.use_fast(True)
        try:
            js = Compiler.compile(inp, test.path, out='js', warn=self.warn)
        except:
            self.compile_fail(inp, test, 'js')
        else:
            self.log('--js:\n', js)
            c = test.out('.js', js, False)
            self.log('->', c)
            jsrun = runjsfile(c).rstrip() + '\n'
            jsout = test.out('.js.html', jsrun, self.compare, self.update)

        if pyrun and jsrun and pyrun != jsrun:
            self.run_mismatch(pyout, jsout)
        return self.done(test)

    def compile_fail(self, inp, test, target):
        print 'Compile failed:', test.path, '->', target
        raise

    def compare(self, outf, expectf):
        # files do not match - return outf to keep processing
        raise AssertionError("%s != %s" % (outf, expectf))

    def done(self, test):
        for w in self.expected_warnings:
            self.log('Expected warning:', w)
        return True

    def run_mismatch(self, pyout, jsout):
        self.log("WARNING: %s and %s output should match" % (pyout, jsout))
        self.log("diff", pyout, jsout)
        #os.system("diff %s %s" % (pyout, jsout))

class VerboseRunner(Runner):
    fail = mismatch = 0

    def start(self, test):
        self.log('----', test.path)
        self.fail = self.mismatch = 0

    def log(self, *args):
        print ' '.join(map(unicode, args))

    def compare(self, outf, expectf):
        # files do not match - return outf to keep processing
        self.log("Failed! %s != %s" % (outf, expectf))
        self.fail = 1
        return outf

    def done(self, test):
        self.log("head %s.*" % test.outbase)
        return not (self.fail or self.mismatch)

    def run_mismatch(self, pyout, jsout):
        self.mismatch = 1
        self.log("WARNING: %s and %s output should match" % (pyout, jsout))
        self.log("diff", pyout, jsout)
        self.log(os.popen("diff %s %s" % (pyout, jsout)).read().decode('utf8'))

    def compile_fail(self, inp, test, target):
        print 'Compile failed:', test.path, '->', target
        traceback.print_exc()
        print '-----'
        print inp
        print '-----'
        self.fail = True

    def runpy_failed(self, test, py):
        print 'Runpy failed:', test.path,
        traceback.print_exc()
        print '-----'
        print py
        print '-----'
        self.fail = True

class VerboseOnFailRunner(VerboseRunner):
    logs = None
    def log(self, *args):
        if self.logs is None:
            self.logs = []
        self.logs.append(args)

    def start(self, test):
        VerboseRunner.start(self, test)
        print '----', test.path
        self.logs = []

    def done(self, test):
        r = VerboseRunner.done(self, test)
        if not r:
            def uni(s):
                try: return unicode(s)
                except: return repr(s)
            for args in self.logs:
                print ' '.join(map(uni, args))
        else:
            print '---> Test ok', test.file
        return r

def runpy(pycode):
    d = {}
    exec pycode in d, d
    return d['html'](a='a', b=[1, 2], c=1, d={'a':'AA', 'b': [1,2,3]})

def runjsfile(jsfile):
    rel_mod = os.path.splitext(jsfile)[0]
    assert "\\" not in rel_mod
    assert "'" not in rel_mod
    data = "{a: 'a', b: [1, 2], c:1, d: {a:'AA', b: [1,2,3]}}"
    js = "require('./%s').html.call(%s)+'';" % (rel_mod, data)
    assert '"' not in js
    cmd = 'node -p -e "%s" 2>&1' % js
    print>>sys.stderr, cmd
    return os.popen(cmd).read().decode('utf8')

if __name__ == '__main__':
    print "Running tests... (pass -u to update)"
    io = cStringIO.StringIO()

    import sys
    sys.path.append('.')   # include tatlrt.py
    sys.path.append('tests/out') # so that tests can import each other

    ExprSemantics.DEBUG = True

    args = sys.argv[1:]
    update = '-u' in args
    if update: args.remove('-u')
    verbose = '-v' in args
    if verbose:
        args.remove('-v')
        runner = VerboseOnFailRunner(update)
    else:
        runner = Runner(update)
    keepgoing = '-c' in args
    if keepgoing: args.remove('-c')

    try:
        test_grammar(update)

        fails = []
        for fn, test in test_tatl():
            if not args or test.path in args:
                #import pdb
                #pdb.set_trace()
                ok = runner.runtest(test)
                if ok: continue
                fails.append(test.path)
                if not keepgoing:
                    break
        for f in fails:
            print f
    except Exception, e:
        traceback.print_exc()
        sys.exit(1)
