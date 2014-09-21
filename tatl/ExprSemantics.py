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
        return IR.AsgnIf(IR.Rvar(ast.var), ast.expr)

    def lset(self, ast):
        return IR.Asgn(ast.lvar, ast.expr)

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
        return IR.Member(ast.key, ast.val)

    def barename(self, name):
        return IR.Str(name)

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

    @debug
    def comp(self, ast):
        if len(ast) == 1:
            return IR.Bool(ast[0])
        else:
            # ast is arg, op, arg2, op, arg3 etc
            args, ops = ast[::2], ast[1::2]
            return IR.OpChain(args, ops)

    def relit(self, ast):
        return ast[1:-1]

    def regex(self, ast):
        return IR.Regex(ast.re, '!' in ast.op, ast.expr)

    def ternary(self, ast):
        if not (ast.true or ast.false):
            # test ?
            return ast.test
        elif ast.true:
            # test ? true  /  test ? true : false
            return IR.Ternary(ast.test, ast.true, ast.false or IR.Null)
        else:
            # test ?: false
            return IR.Or(ast.test, ast.false)

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
        rest = self._rest(ast.parseinfo)
        return IR.Top(ast.set_ or [], ast.exprs or [], ast.emit, rest)

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
        return IR.If(ast.set_ or [], ast.test)

    def forExpr(self, ast):
        if ast.n2:
            stmt = IR.For2(ast.n1, ast.n2, ast.expr)
        else:
            stmt = IR.For1(ast.n1 or IR.Lvar('dot'), ast.expr)
        if ast.pragma:
            stmt.pragma(ast.pragma[1:].strip())
        return IR.For(ast.set_ or [], stmt)

    def lvar(self, ast):
        return IR.Lvar(ast)

    def paramExpr(self, ast):
        return ast

    def callargs(self, ast):
        return [] if ast == ['(', ')'] else ast

    def useExpr(self, ast):
        # step, path, arglist
        return IR.Use(ast.set_ or [], ast.path, ast.arglist)
