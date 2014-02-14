import ExprParser

class Coder(object):
    # Encode things that may vary in syntax depending on how runtime
    # and compiler works
    def path(self, args):
        return '.'.join(args)

    def dotpath(self, args):
        args[0] = 'dot'
        return '.'.join(args)

    def extpath(self, module, path):
        return '__import__(%r).%s' % (module, '.'.join(path))

    def arglist(self, args):
        return ', '.join(args)

    def regex(self, regex, expr):
        return 'bool(re.search(%r, %s))' % (regex, expr)

    def top(self, asgn, exprs, emitexpr, star):
        if exprs:
            asgn.extend(exprs)
        if star:
            type, name = star
            if type == '++':
                fn = 'lambda o, _n=[0]: _n[0]++' 
            else:
                fn = 'lambda o, _a=reserve(): _a.append(quote(o))'
            asgn.append('%s = %s' % (name, fn))
        if emitexpr:
            asgn.append('emit(%s)' % emitexpr)
        return '\n'.join(asgn)
        
    def set(self, name, filter, contents):
        result = '_.pop()'
        for filt in filter or []:
            result = '%s( %s )' % (filt, result)
        return '%s = %s #%s' % (name, result, contents)
           
    def funcdef(self, name, args, filters):
        lines = ['@'+filt for filt in filters] + ['def %s(%s):' % (name, args)]
        return '\n'.join(lines)
        
    def if_stmt(self, test):
        return 'if %s:' % test
        
    def for2(self, n1, n2, rvar):
        return self.for1(n1+','+n2, 'items(%s)' % rvar)
        
    def for1(self, n1, rvar):
        return 'for %s in %s:' % (n1, rvar)

    def for0(self, rvar):
        return self.for1('dot', rvar)    
        
    def assign(self, lvar, expr):
        return '%s = %s' % (lvar, expr)
        
    def lookup(self, path, key):
        return '%s[%s]' % (path, key)
        
    def star(self, type, name):
        return type, name
                
class ExprSemantics(ExprParser.ExprParser):
    "Build Python code. Try to eval/compile early to catch issues as parse tree is built."
    def __init__(self, coder):
        self.c = coder
        
    def filter(self, ast):
        return ast

    def star(self, ast):
        type, name = ast
        return self.c.star(type, name)

    def filtexp(self, ast):
        result = str(ast.expr)
        for filt in ast.filter or []:
            result = '%s( %s )' % (filt, result)
        return result

    def set(self, ast):
        return self.c.assign(ast.lvar, ast.expr)

    def dottedPath(self, ast):
        return self.c.path(ast)

    def dotPath(self, ast):
        return self.c.dotpath(ast)

    def externalPath(self, ast):
        return self.c.extpath(ast.module, ast.path)

    def path(self, ast):
        if ast.lookup:
            return self.c.lookup(ast.path, ast.lookup)
        return ast.path

    def number(self, ast):
        eval(ast)
        return ast

    def string(self, ast):
        eval(ast)
        return ast
        
    def map(self, ast):
        if ast == ['{', '}']:
            return '{}'
        else:
            return '{%s}' % ', '.join(ast)

    def member(self, ast):
        key = repr(str(ast.nkey)) if ast.nkey else ast.skey
        return '%s: %s' % (key, ast.val)

    def range(self, ast):
        arg1, op, arg2 = ast
        if op == '...': arg2 += ' + 1'
        return 'range(%s, %s)' % (arg1, arg2)

    def comp(self, ast):
        if len(ast) == 1:
            return 'bool(%s)' % ast[0]
        else:
            return ' '.join(ast)

    def regex(self, ast):
        return self.c.regex(ast.re[1:-1], ast.expr)

    def ternary(self, ast):
        return '%(true)s if %(test)s else %(false)s' % ast

    def list(self, ast):
        if ast == ['[', ']']: return '[]'
        if isinstance(ast[-1], list):
            ast[-1] = ''.join(ast[-1])
        return '[%s]' % ', '.join(ast)

    def call(self, ast):
        return '%s(%s)' % (ast.fn, ', '.join(ast.arg or []))

    def PYEXPR(self, ast):
        py_code = ''.join(ast[1:-1])
        compile(py_code, py_code, 'eval')
        return py_code

    def arg(self, ast):
        return ast
        
    def arglist(self, ast):
        if ast == ['(', ')']:
            return self.c.arglist([])
        return self.c.arglist(ast)
    
    # externally called...
    def top(self, ast):
        """
        top = '{' {set+:set ';'} {exprs+:expr ';'} emit:[ topemitexpr ] '}' ;
        topemitexpr = star:starexp | filtexp:expr ;
        """
        e = ast.emit
        return self.c.top(ast.set or [], ast.exprs or [], e and e.filtexp, e and e.star), self._rest(ast.parseinfo)

    def _rest(self, p):
        if not p: return None  # check!
        return p.buffer.text[p.endpos:]
        
    def defExpr(self, ast):
        return self.c.funcdef(ast.name, ast.args, ast.filter or [])
        
    def setExpr(self, ast):
        f = ast.filter or []
        tag = 'tag' in f
        contents = 'contents' in f
        if not f or not (tag or contents):
            raise SyntaxError('set="" must include |tag or |contents as a filter')
        if tag and contents:
            raise SyntaxError('set="" cannot include both |tag and |contents as a filter')
        if tag: f.remove('tag')
        if contents: f.remove('contents')
        return self.c.set(ast.name, ast.filter or [], contents)

    def ifExpr(self, ast):
        return self.c.if_stmt(ast)
        
    def forExpr(self, ast):
        if ast.n2:
            return self.c.for2(ast.n1, ast.n2, ast.expr)
        elif ast.n1: 
            return self.c.for1(ast.n1, ast.expr)
        else:
            return self.c.for0(ast.expr)

    def paramExpr(self, ast):
        return ast
        
        
