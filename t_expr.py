import ExprParser, ExprSemantics
import json
import os, sys, re
import readline
import traceback

def varref(v): print 'varref:', v
def modref(m): print 'modref:', m

TEST = 'Expr.tests/%s.txt'

mtime = lambda f=__file__: os.stat(f).st_mtime
touch = mtime()
def compile():
    global parser, touch
    if touch < mtime():
        if raw_input('Restart?') == 'y':
            os.execl(sys.executable, *([sys.executable]+sys.argv))
        else:
            touch = mtime()
    if mtime('Expr.ebnf') > mtime('ExprParser.py'):
        os.system("grako -o ExprParser.py Expr.ebnf")
        reload(ExprParser)
    reload(ExprSemantics)
    coder = ExprSemantics.Coder()
    parser = ExprParser.ExprParser(
        parseinfo=parseinfo, 
        semantics=ExprSemantics.ExprSemantics(coder)
    )
 

def analyze_cycles(tb):
    while tb is not None:
        co = tb.tb_frame.f_code
        if 'ExprParser' in co.co_filename:
            print co.co_name
        tb = tb.tb_next

def runtests():
    if not tests:
        print '(no tests for %s)' % rule
        print
        return
        
    maxlen = max(map(len, tests))
    for i, test in enumerate(tests):
        try:
            result = parser.parse(test, rule_name=rule)
        except Exception, e:
            result = 'ERROR: ' + str(e)
            result = result.replace('\n', ' ')[:max(40, 72-maxlen)]
        print '%2d> %s | %s' % (i+1, test.ljust(maxlen), result)
    print

settest_inp = re.compile('>(\d+)?\s*([+-=]\s*)(.*)')
def settest(m):
    global tests
    ix, op, test = m.groups()
    if not ix: 
        if op == '-':
            print "Specify a number"
            return
        ix = len(tests)
    else:
        ix = int(ix)-1
    test = test or last
    if op == '-':
        del tests[ix]
    elif op == '+' or ix >= len(tests):
        tests.insert(ix, test)
    else:
        tests[ix] = test
    open(TEST % rule, 'w').write('\n'.join(tests)+'\n')
 
def loadtests():
    global tests
    f = TEST % rule
    if os.path.exists(f):
        tests = open(f).read().splitlines()
    else:
        tests = []
    
parseinfo = False
compile()
rule = 'attrs'
loadtests()
trace=False
print '>rule changes rulename'
print 'trace on|off changes tracing'
print 'info on|off changes parseinfo'
print 'No input recompiles'
e = None
last = None
while 1:
    runtests()
    try:
        inp = raw_input(('[I]' if parseinfo else '')+('[T]' if trace else '')+rule+'>')
        if settest_inp.match(inp):
            settest(settest_inp.match(inp))
            continue
        elif inp.startswith('>'):
            rule = inp[1:]
            loadtests()
            continue
        if inp.startswith('trace '):
            trace = bool(['off', 'on'].index(inp[6:]))
            continue
        if inp.startswith('info '):
            parseinfo = bool(['off', 'on'].index(inp[5:]))
            compile()
            print chr(27) + "[2J;"
            continue
        if not inp:
            if e:
                traceback.print_exc()
                e = None
                continue
            else:
                compile()
                continue
        last = inp
        ast = parser.parse(inp, rule_name=rule, trace=trace)
        print('AST:')
        print(ast)
        print
        print('JSON:')
        print(json.dumps(ast, indent=2))
        print
        e = None
    except KeyboardInterrupt:
        break
    except RuntimeError, e:
        print 'error:', repr(e), e
        analyze_cycles(sys.exc_info()[2])
    except Exception, e:
        print 'error:', repr(e), e
