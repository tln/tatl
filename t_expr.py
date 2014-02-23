import os

# Generate if needed
if not os.path.exists('ExprParser.py'):
    os.system("grako -o ExprParser.py Expr.ebnf")

import ExprParser

import ExprSemantics, t_compile, IR, OpList, t_tmpl
import json
import os, sys, re
import readline
import traceback, pdb

def varref(v): print 'varref:', v
def modref(m): print 'modref:', m

TEST = 'Expr.tests/%s.txt'

mtime = lambda f=__file__: os.stat(f).st_mtime
touch = mtime()
def compile():
    global parser, touch
    if touch < mtime():
        if raw_input('Restart?') == 'y':
            os.execl(sys.executable, *([sys.executable]+sys.argv[:1]+[rule, out]))
        else:
            touch = mtime()
    if mtime('Expr.ebnf') > mtime('ExprParser.py'):
        os.system("grako -o ExprParser.py Expr.ebnf")
        reload(ExprParser)
    reload(OpList)
    reload(IR)
    reload(ExprSemantics)
    reload(t_tmpl)
    reload(t_compile)
    parser = ExprParser.ExprParser(
        parseinfo=parseinfo, 
        semantics=ExprSemantics.ExprSemantics()
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
        
    W, H = getTerminalSize()
    maxlen = max(map(len, tests))
    fmt = '%2d> %s | %s'
    ofs = len(fmt%(1,'',''))
    for i, test in enumerate(tests):
        try:
            result = str(run(test))
        except Exception, e:
            result = 'ERROR: ' + str(e)
        n = maxlen+ofs
        ind = ' '*n
        result = '\n'.join([ind+line[:W-n-1] for line in result.splitlines()])[n:]
        print fmt % (i+1, test.ljust(maxlen), result)
    print

settest_inp = re.compile('>(\d+)?\s*([+-=])\s*(.*)')
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
   
def getTerminalSize():
    import os
    env = os.environ
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        except:
            return
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))

        ### Use get(key[, default]) instead of a try/catch
        #try:
        #    cr = (env['LINES'], env['COLUMNS'])
        #except:
        #    cr = (25, 80)
    return int(cr[1]), int(cr[0])

def run(inp, debug=0):  
    if rule[:2] == 'c.':
        if debug:
            pdb.set_trace()
        code = t_compile.compile(inp, '<py>', out=out[-2:])
        if out == 'runpy':
            d = {}
            exec code in d, d
            return d['html'](a='a', b=[1, 2], c=1, d={'a':'AA', 'b': [1,2,3]})
        elif out in ('runjs', 'run+js'):
            with open('_tmp.js', 'w') as f:
                f.write(code+'\n\n')
                f.write('''console.log(html.call({a:'a', b:[1,2], c:1, d:{'a':'AA', 'b': [1,2,3]}}))\n''')
            result = os.popen('node _tmp.js 2>&1').read()
            if out == 'run+js':
                return code + '\n\n' + result
        else:
            return code
    else:
        ExprSemantics.DEBUG = debug
        ast = parser.parse(inp, rule_name=rule, trace=trace)
        if hasattr(ast, 'out'):
            return ast.out()
        return ast  # warning?

args = sys.argv[1:3]
rule, out = args + ['attrs', 'py'][len(args):]
parseinfo = False
compile()
loadtests()
trace=False
print '>rule changes rulename'
print 'trace on|off changes tracing'
print 'info on|off changes parseinfo'
print 'No input recompiles'
e = None
last = None
while 1:
    #print OpList.all - OpList.used
    try:
        inp = raw_input(('[I]' if parseinfo else '')+('[T]' if trace else '')+rule+'>')
        runtests()
        if settest_inp.match(inp):
            settest(settest_inp.match(inp))
            continue
        elif inp.startswith('>'):
            inp = inp[1:]
            if inp.isdigit():
                inp = tests[int(ix)-1]
            else:
                rule = inp
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
        if inp.startswith('out '):
            out = inp[4:]
            inp - last
        if inp == 'unused':
            print t_
        if not inp:
            if e:
                e = None
                traceback.print_exc()
                try: run(last, debug=1)
                except:
                    import traceback
                    traceback.print_exc()
                continue
            else:
                compile()
                continue
        print '----'
        print inp
        last = inp
        ast = run(inp)
        print(ast)
        print
        e = None
    except KeyboardInterrupt:
        break
    except RuntimeError, e:
        print 'error:', repr(e), e
        analyze_cycles(sys.exc_info()[2])
    except pdb.bdb.BdbQuit:
        pass
    except Exception, e:
        print 'error:', repr(e), e
