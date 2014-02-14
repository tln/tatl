import ExprParser, ExprSemantics
import json
import os
import readline
import traceback

def varref(v): print 'varref:', v
def modref(m): print 'modref:', m

def compile():
    global parser
    os.system("grako -o ExprParser.py Expr.ebnf")
    reload(ExprParser)
    reload(ExprSemantics)
    coder = ExprSemantics.Coder()
    parser = ExprParser.ExprParser(
        parseinfo=parseinfo, 
        semantics=ExprSemantics.ExprSemantics(coder)
    )


parseinfo = False
compile()
rule = 'top'
trace=False
print '>rule changes rulename'
print 'trace on|off changes tracing'
print 'info on|off changes parseinfo'
print 'No input recompiles'
e = None
while 1:
    try:
        inp = raw_input(('[I]' if parseinfo else '')+('[T]' if trace else '')+rule+'>')
        if inp.startswith('>'):
            rule = inp[1:]
            continue
        if inp.startswith('trace '):
            trace = bool(['off', 'on'].index(inp[6:]))
            continue
        if inp.startswith('info '):
            parseinfo = bool(['off', 'on'].index(inp[5:]))
            compile()
            continue
        if not inp:
            if e:
                traceback.print_exc()
                e = None
                continue
            else:
                compile()
                continue
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
    except Exception, e:
        print 'error:', repr(e), e
