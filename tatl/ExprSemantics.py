from tatl import ExprParser, IR

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
        return IR.Placeholder(ast)

    def starexp(self, ast):
        return IR.StarExp(ast)

    def filter(self, ast):
        return IR.Filt(ast)

    def filtexp(self, ast):
        result = ast.expr
        for filt in ast.filter or []:
            result = IR.FiltExp(result, filt)
        return result

    def setif(self, ast):
        n = ast.var
        fmt = '{0} = %(0)s {1} %(1)s'.format
        result = IR.Part(fmt(n, 'or'), fmt(n, '||'), IR.Expr([n], n, n), ast.expr)
        result.out()
        return result

    def lset(self, ast):
        fmt = '%(lvar)s = %(expr)s'
        return IR.Part(fmt, fmt, lvar=ast.lvar, expr=ast.expr)

    def dottedPath(self, ast):
        return IR.Path(ast)

    def dotPath(self, ast):
        ast[0] = 'dot'
        return self.dottedPath(ast)

    def externalPath(self, ast):
        return IR.ExtPath(ast.module, ast.path)

    def path(self, ast):
        if ast.lookup:
            return IR.Lookup(ast.path, ast.lookup)
        return ast.path

    def pname(self, ast):
        if ast in IR.RESERVED:
            raise SyntaxError("%r is a reserved name" % ast)
        if ast[:1] == '_':
            raise SyntaxError("names beginning with underscores are reserved")
        return ast

    def name(self, ast):
        if ast == '.':
            return 'dot'
        if ast[:1] == '_':
            raise SyntaxError("names beginning with underscores are reserved")
        if ast in IR.RESERVED:
            return '_'+ast
        return ast

    def number(self, ast):
        return IR.Value(ast)

    def string(self, ast):
        return IR.Value(ast)

    def map(self, ast):
        if ast == ['{', '}']:
            return IR.Expr([], '{}')
        return self._join_with_star(ast, '{%s}', ', ', 'merge(%s)')

    def member(self, ast):
        return IR.Part('%(0)s: %(1)s', '%(0)s: %(1)s', ast.key, ast.val)

    def barename(self, name):
        return IR.Value(repr(name))

    def range(self, ast):
        arg1, op, arg2 = ast
        return {'..': IR.RangeExcl, '...': IR.RangeIncl}[op](arg1, arg2)

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
            return IR.Part('bool(%(0)s)', 'tatlrt.bool(%(0)s)', ast[0])
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
            return IR.Part(pyfmt, jsfmt, *args)

    def relit(self, ast):
        return ast[1:-1]

    def regex(self, ast):
        pyop, jsop = ('not ', '!') if '!' in ast.op else ('','')
        re = ast.re.replace('%', '%%')
        pyfmt = pyop + '_.search(%r, %%(0)s)' % re
        jsfmt = jsop + '_.search(/%s/, %%(0)s)' % re
        return IR.Part(pyfmt, jsfmt, ast.expr)

    def ternary(self, ast):
        if not (ast.true or ast.false):
            # test ?
            return ast.test
        elif ast.true:
            # test ? true  /  test ? true : false
            return IR.Part(
                '%(true)s if %(test)s else %(false)s',
                '%(test)s ? %(true)s : %(false)s',
                test=ast.test, true=ast.true,
                false=ast.false or IR.Expr([], 'None', 'null'),
                )
        else:
            # test ?: false
            return IR.Part(
                '(%(test)s or %(false)s)',
                '((%(test)s) || (%(false)s))',
                test=ast.test, false=ast.false
                )

    def list(self, ast):
        if ast == ['[', ']']: return IR.Expr([], '[]')
        return self._join_with_star(ast, '[%s]',
            {'py': '+', 'js':','},
            {'py': '%s', 'js': '[].concat(%s)'})

    @debug
    def _join_with_star(self, ast, paren, join, outer='%s'):
        parts = []
        expr = []
        for p in ast:
            if isinstance(p, IR.StarExp):
                if expr:
                    parts.append(IR.List(expr, paren=paren))
                    expr = []
                parts.append(p)
            else:
                expr.append(p)
        if expr:
            parts.append(IR.List(expr, paren=paren))
        if len(parts) == 1:
            parts = parts[0]
        else:
            parts = IR.List(parts, join, outer)
        parts.out() # check its ok
        return parts

    def call(self, ast):
        return IR.Call(ast.fn, ast.arg or [])

    def PYEXPR(self, ast):
        py_code = ''.join(ast[1:-1])
        compile(py_code, py_code, 'eval')
        return py_code

    def arg(self, ast):
        return IR.STAR_ARG if ast == '*' else IR.Lvar(ast)

    def arglist(self, ast):
        assert ast.pop() == ')'
        return IR.Args(ast)

    # externally called...
    def top(self, ast):
        """
        top = '{' {set+:set ';'} {exprs+:expr ';'} emit:[ topemitexpr ] '}' ;
        topemitexpr = star:placeholder | filtexp:expr ;
        """
        if not hasattr(ast, 'parseinfo'):
            import pdb
            pdb.set_trace()
        rest = self._rest(ast.parseinfo)
        return IR.Top(ast.set or [], ast.exprs or [], ast.emit, rest)

    def _rest(self, p):
        if not p: return None  # check!
        return p.buffer.text[p.endpos:]

    def defExpr(self, ast):
        return IR.Def(ast.name,
            ast.args or IR.Args([IR.STAR_ARG]),
            ast.result,
            ast.filter or [])

    @debug
    def setExpr(self, ast):
        return IR.Set(ast.var, ast.filter or [])

    def ifExpr(self, ast):
        return IR.If(ast.set or [], ast.test)

    def forExpr(self, ast):
        if ast.n2:
            stmt = IR.For2(ast.n1, ast.n2, ast.expr)
        else:
            stmt = IR.For1(ast.n1 or IR.Lvar('dot'), ast.expr)
        if ast.pragma:
            stmt.pragma(ast.pragma[1:].strip())
        return IR.For(ast.set or [], stmt)

    def lvar(self, ast):
        return IR.Lvar(ast)

    def paramExpr(self, ast):
        return ast

    def callargs(self, ast):
        return [] if ast == ['(', ')'] else ast

    def useExpr(self, ast):
        # step, path, arglist
        return IR.Use(ast.set or [], ast.path, ast.arglist)
