import ExprParser
from collections import namedtuple
DEBUG=0
class BasePart:
    """Represents part of our AST. Renders early to py or js, keeps 
    tracks of lvars and rvars of itself and children.
    """
    py = js = '*not implemented*'
    def __init__(self):
        self.lvars = []
        self.rvars = []
        
    def add(self, part):
        self.lvars.extend(part.lvars)
        self.rvars.extend(part.rvars)
        
    def __str__(self):
        #TODO remove
        print 'str called -> %r' % self.py
        return self.py
        
    def __repr__(self):
        return '<%s>' % self.out().replace('\n', ' ')
        
    type = ''
    def out(self):
        l = []
        if self.py == self.js:
            l.append('py/js: '+self.py)
        else:
            l.append('py: '+self.py)
            l.append('js: '+self.js)
        line = ''
        if self.type:
            line += 'type: %s ' % self.type
        if self.lvars:
            line += 'lvars: %s ' % ','.join(self.lvars)
        if self.rvars:
            line += 'rvars: %s ' % ','.join(self.rvars)
        line = line.rstrip()
        if line:
            l.append(line)
        return '\n'.join(l)
            

class Part(BasePart):
    def __init__(self, pyfmt, jsfmt, *parts, **partkw):
        BasePart.__init__(self)
        pyfrags = {}
        jsfrags = {}
        for k, v in list(enumerate(parts)) + partkw.items():
            self.add(v)
            pyfrags[str(k)] = v.py
            jsfrags[str(k)] = v.js
        self.py = pyfmt % pyfrags
        self.js = jsfmt % jsfrags
        self.__dict__.update(partkw)
      
class List(BasePart):
    def __init__(self, partlist, join=', '):
        BasePart.__init__(self)
        self.partlist = partlist
        map(self.add, partlist)
        self.py = join.join(p.py for p in partlist)
        self.js = join.join(p.js for p in partlist)

class Lvar(BasePart):
    def __init__(self, lvar):
        BasePart.__init__(self)
        self.lvars = [lvar]
        self.py = self.js = lvar
        
class Expr(BasePart):
    def __init__(self, rvars, py, js=None):
        BasePart.__init__(self)
        self.py = py
        self.js = js or py
        self.rvars = rvars
        
class Value(BasePart):
    def __init__(self, py, js=None):
        BasePart.__init__(self)        
        self.py = py
        self.js = js or py
 
 
class Wrap(BasePart):
    def __init__(self, part):
        BasePart.__init__(self)
        self.add(part)
        self.py = part.py
        self.js = part.js
        self.part = part
class StarExp(Wrap):
    type = 'starexp'
 
class StarArg(BasePart):
    py = js = '*star*'
STAR_ARG = StarArg()

class Args(List):
    def args(self):
        return ['*' if p is STAR_ARG else p.lvar
                for p in self.partlist]

class Placeholder(BasePart):
    type = 'placeholder'
    def __init__(self, ast):
        BasePart.__init__(self)
        op, self.name = ast
        self.type = {'*':'star','++':'plusplus'}[op]
        self.py = self.js = '%s = _.%s()' % (self.name, self.type)
        self.lvars = [self.name]

class Out:
    # mixin to namedtuples
    def out(self):
        l = []
        for k in self._fields:
            v = getattr(self, k)
            if v and isinstance(v, list):
                l += [('%s[%s]' % (k, ix), v.out() if hasattr(v, 'out') else str(v)) 
                      for ix, v in enumerate(v)]
            else:
                v = v.out() if hasattr(v, 'out') else str(v)
                l.append((k, v))
        n = max(len(lbl) for lbl, val in l)
        s = '\n' + ' '*n + '   '
        return '\n'.join(
            lbl.ljust(n)+' = '+val.replace('\n', s)
            for lbl, val in l
        )


class Def(namedtuple('Def', 'name args result filter'), Out): pass
class If(namedtuple('If', 'set test'), Out): pass
class Use(namedtuple('Use', 'set path arglist'), Out): pass
class For(namedtuple('For', 'set stmt'), Out): pass
class Top(namedtuple('Top', 'set exprs emit rest'), Out): pass

def debug(retry):
    def inner(*args, **kw):
        try:
            return retry(*args, **kw)
        except:
            if DEBUG:
                import pdb
                pdb.set_trace()
                retry(*args, **kw)
                assert not "reached"
            raise
    return inner
 
class ExprSemantics(ExprParser.ExprParser):
    "Build Python code. Try to eval/compile early to catch issues as parse tree is built."
    def placeholder(self, ast):
        return Placeholder(ast)
        
    def starexp(self, ast):
        return StarExp(ast)

    def filtexp(self, ast):
        result = ast.expr
        fmt = '%(0)s( %(1)s )'
        for filt in ast.filter or []:
            result = Part(fmt, fmt, filt, result)
        return result

    def setif(self, ast):
        n = ast.lvar
        fmt = '{0} = %(0)s {1} %(1)s'.format
        return Part(fmt(n, 'or'), fmt(n, '||'), Expr([n], n, n), ast.expr)
    
    def set(self, ast):
        fmt = '%(lvar)s = %(expr)s'
        return Part(fmt, fmt, lvar=ast.lvar, expr=ast.expr)

    def dottedPath(self, ast):
        return Expr([ast[0]], '.'.join(ast))

    def dotPath(self, ast):
        ast[0] = 'dot'
        return self.dottedPath(ast)

    def externalPath(self, ast):
        return Expr([], '_.require(%r).%s' % (ast.module, '.'.join(ast.path)))

    def path(self, ast):
        if ast.lookup:
            fmt = '%(0)s[%(1)s]'
            return Part(fmt, fmt, ast.path, ast.lookup)
        return ast.path

    def number(self, ast):
        return Value(ast)

    def string(self, ast):
        return Value(ast)
        
    def map(self, ast):
        if ast == ['{', '}']:
            return Expr([], '{}')
        return self._join_with_star(ast, '{%(0)s}', ', ', 'merge(%(0)s)')

    def member(self, ast):
        key = repr(str(ast.nkey)) if ast.nkey else ast.skey
        return Part('%(0)s: %(1)s', '%(0)s: %(1)s', Value(key), ast.val)

    def range(self, ast):
        arg1, op, arg2 = ast
        fmt = {
            '..': 'range(%(0)s, %(1)s)', 
            '...':'range(%(0)s, %(1)s+1)'
        }[op]
        return Part(fmt, fmt, arg1, arg2)

    def eqop(self, op):
        return {
            'eq': '=', 'ne': '!=', '=!': '!='
        }.get(op, op)

    def compop(self, op):
        return {
            'ge':'>=', 'le':'<=', 'gt': '>', 'lt': '<',
            '=<': '<=', '=>':'>='
        }.get(op, op)

    def comp(self, ast):
        if len(ast) == 1:
            return Part('bool(%(0)s)s', 'bool(%(0)s)', ast[0])
        else:
            # ast is arg, op, arg2, op, arg3 etc
            args = ast[::2]

            py = ast[:]
            py[::2] = map('%({})s'.format, range(len(args)))
            pyfmt = ' '.join(py)
            
            if len(ast) == 3:
                jsfmt = '%(0)s '+ ast[1] + ' %(1)s'
            else:
                l = ['%(0)s']
                ix = 1
                for op in ast[1:-2:2]:
                    l += [op, '(_tmp{0} = %({0})s) && _tmp{0}'.format(ix)]
                    ix += 1
                l += [ast[-2], '%({})s'.format(ix)]
                jsfmt = ' '.join(l)
            return Part(pyfmt, jsfmt, *args)

    def relit(self, ast):
        return ast[1:-1]

    def regex(self, ast):
        pyop, jsop = {
            '~': ('is', ''),
            '!~': ('is not', '!'),
            '~!': ('is not', '!')
        }[ast.op]
        re = ast.re.replace('%', '%%')
        pyfmt = 're.search(%r, %%(0)s) %s None' % (re, pyop)
        jsfmt = '%s/%s/.test(%%(0)s)' % (jsop, re)
        return Part(pyfmt, jsfmt, ast.expr)
        
    def ternary(self, ast):
        if ast.true:
            return Part(
                '%(true)s if %(test)s else %(false)s', 
                '%(test)s ? %(true)s : %(false)s',
                test=ast.test, true=ast.true, 
                false=ast.false or Expr([], 'None', 'null'),
                )
        else:
            # test ?: false
            return Part(
                '(%(test)s or %(false)s)', 
                '((%(test)s) || (%(false)s))',
                test=ast.test, false=ast.false
                )

    def list(self, ast):
        if ast == ['[', ']']: return Expr([], '[]')
        return self._join_with_star(ast, '[%(0)s]', '+', '')
    
    def _join_with_star(self, ast, paren, join, outer=''):
        parts = []
        expr = []
        for p in ast:
            if isinstance(p, StarExp):
                if expr:
                    parts.append(Part(paren, paren, List(expr)))
                    expr = []
                parts.append(p)
            else:
                expr.append(p)
        if expr:
            parts.append(Part(paren, paren, List(expr)))
        if len(parts) == 1:
            parts = parts[0]
        else:
            parts = List(parts, join)
            if outer:
                parts = Part(outer, outer, parts)
        parts.out() # check its ok
        return parts
            
    def call(self, ast):
        return Part('%(0)s(%(1)s)', '%(0)s(%(1)s)', ast.fn, List(ast.arg))

    def PYEXPR(self, ast):
        py_code = ''.join(ast[1:-1])
        compile(py_code, py_code, 'eval')
        return py_code

    def arg(self, ast):
        return STAR_ARG if ast == '*' else Lvar(ast)
        
    def arglist(self, ast):
        return Args(ast)
    
    # externally called...
    def top(self, ast):
        """
        top = '{' {set+:set ';'} {exprs+:expr ';'} emit:[ topemitexpr ] '}' ;
        topemitexpr = star:placeholder | filtexp:expr ;
        """
        rest = self._rest(ast.parseinfo)
        return Top(ast.set or [], ast.exprs or [], ast.emit, rest)

    def _rest(self, p):
        if not p: return None  # check!
        return p.buffer.text[p.endpos:]
        
    def defExpr(self, ast):
        return Def(ast.name, ast.args, ast.result, ast.filter or [])
        
    def setExpr(self, ast):
        return ast

    def ifExpr(self, ast):
        return If(ast.set or [], ast.test)
        
    def forExpr(self, ast):
        if ast.n2:
            pyfmt = 'for %(n1)s, %(n2)s in _.items(%(expr)s):'
            jsfmt = 'for (%(n1)s in (_tmp = %(expr)s)) { %(n2)s = _tmp[%(n1)s];'
            stmt = Part(pyfmt, jsfmt, n1=ast.n1, n2=ast.n2, expr=ast.expr)
        else: 
            pyfmt = 'for %(n1)s in _.iter(%(expr)s):'
            jsfmt = 'for (%(n1)s in %(expr)s) {'
            stmt = Part(pyfmt, jsfmt, n1=ast.n1 or Lvar('dot'), expr=ast.expr)
        return For(set=ast.set or [], stmt=stmt)
            
    def lvar(self, ast):
        return Lvar(ast)

    def paramExpr(self, ast):
        return ast
        

    @debug
    def useExpr(self, ast):
        # step, path, arglist
        return Use(ast.set or [], ast.path, ast.arglist and List(ast.arglist))
