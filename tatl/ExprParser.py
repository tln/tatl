#!/usr/bin/env python
# -*- coding: utf-8 -*-

# CAVEAT UTILITOR
#
# This file was automatically generated by Grako.
#
#    https://pypi.python.org/pypi/grako/
#
# Any changes you make to it will be overwritten the next time
# the file is generated.


from __future__ import print_function, division, absolute_import, unicode_literals
from grako.parsing import graken, Parser


__version__ = (2014, 9, 18, 23, 37, 19, 3)

__all__ = [
    'ExprParser',
    'ExprSemantics',
    'main'
]


class ExprParser(Parser):
    def __init__(self, whitespace=None, nameguard=True, **kwargs):
        super(ExprParser, self).__init__(
            whitespace=whitespace,
            nameguard=nameguard,
            **kwargs
        )

    @graken()
    def _defAttr_(self):
        self._defExpr_()
        self._check_eof()

    @graken()
    def _forAttr_(self):
        self._forExpr_()
        self._check_eof()

    @graken()
    def _ifAttr_(self):
        self._ifExpr_()
        self._check_eof()

    @graken()
    def _paramAttr_(self):
        self._paramExpr_()
        self._check_eof()

    @graken()
    def _setAttr_(self):
        self._setExpr_()
        self._check_eof()

    @graken()
    def _useAttr_(self):
        self._useExpr_()
        self._check_eof()

    @graken()
    def _attrs_(self):
        with self._choice():
            with self._option():
                self._token('def="')
                self._defExpr_()
                self.ast['@'] = self.last_node
                self._token('"')
            with self._option():
                self._token('for="')
                self._forExpr_()
                self.ast['@'] = self.last_node
                self._token('"')
            with self._option():
                self._token('if="')
                self._ifExpr_()
                self.ast['@'] = self.last_node
                self._token('"')
            with self._option():
                self._token('param="')
                self._paramExpr_()
                self.ast['@'] = self.last_node
                self._token('"')
            with self._option():
                self._token('set="')
                self._setExpr_()
                self.ast['@'] = self.last_node
                self._token('"')
            with self._option():
                self._token('use="')
                self._useExpr_()
                self.ast['@'] = self.last_node
                self._token('"')
            with self._option():
                self._top_()
            self._error('no available options')

    @graken()
    def _defExpr_(self):
        self._lvar_()
        self.ast['name'] = self.last_node
        with self._optional():
            self._arglist_()
            self.ast['args'] = self.last_node
        with self._optional():
            self._token('=')
            self._expr_()
            self.ast['result'] = self.last_node

        def block3():
            self._filter_()
            self.ast.setlist('filter', self.last_node)
        self._closure(block3)
        with self._optional():
            self._COMMENTQ_()

        self.ast._define(
            ['name', 'args', 'result'],
            ['filter']
        )

    @graken()
    def _arglist_(self):
        self._token('(')
        with self._optional():
            self._arg_()
            self.ast.setlist('@', self.last_node)

            def block1():
                self._token(',')
                self._arg_()
                self.ast.setlist('@', self.last_node)
            self._closure(block1)
            with self._optional():
                self._token(',')
        self._token(')')
        self.ast.setlist('@', self.last_node)

    @graken()
    def _arg_(self):
        with self._choice():
            with self._option():
                self._name_()
                self.ast['@'] = self.last_node
            with self._option():
                self._token('*')
                self.ast['@'] = self.last_node
            self._error('expecting one of: *')

    @graken()
    def _name_(self):
        with self._choice():
            with self._option():
                self._NAME_()
            with self._option():
                self._token('.')
            self._error('expecting one of: .')

    @graken()
    def _setExpr_(self):
        self._lvar_()
        self.ast['var'] = self.last_node

        def block1():
            self._filter_()
            self.ast.setlist('filter', self.last_node)
        self._closure(block1)
        with self._optional():
            self._COMMENTQ_()

        self.ast._define(
            ['var'],
            ['filter']
        )

    @graken()
    def _forExpr_(self):

        def block0():
            self._set_()
            self.ast.setlist('set', self.last_node)
            with self._optional():
                self._COMMENTSQ_()
            self._token(';')
        self._closure(block0)
        with self._optional():
            self._lvar_()
            self.ast['n1'] = self.last_node
            with self._optional():
                self._token(',')
                self._lvar_()
                self.ast['n2'] = self.last_node
            self._token('in')
        self._expr_()
        self.ast['expr'] = self.last_node
        with self._optional():
            self._forpragma_()
            self.ast['pragma'] = self.last_node

        self.ast._define(
            ['n1', 'n2', 'expr', 'pragma'],
            ['set']
        )

    @graken()
    def _forpragma_(self):
        self._COMMENTQ_()

    @graken()
    def _ifExpr_(self):

        def block0():
            self._set_()
            self.ast.setlist('set', self.last_node)
            with self._optional():
                self._COMMENTSQ_()
            self._token(';')
        self._closure(block0)
        self._test_()
        self.ast['test'] = self.last_node
        with self._optional():
            self._COMMENTQ_()

        self.ast._define(
            ['test'],
            ['set']
        )

    @graken()
    def _paramExpr_(self):
        self._lvar_()
        self.ast.setlist('@', self.last_node)

        def block1():
            self._token(',')
            self._lvar_()
            self.ast.setlist('@', self.last_node)
        self._closure(block1)
        with self._optional():
            self._COMMENTQ_()

    @graken()
    def _useExpr_(self):

        def block0():
            self._set_()
            self.ast.setlist('set', self.last_node)
            with self._optional():
                self._COMMENTSQ_()
            self._token(';')
        self._closure(block0)
        self._path_()
        self.ast['path'] = self.last_node
        with self._optional():
            self._callargs_()
            self.ast['arglist'] = self.last_node
        with self._optional():
            self._COMMENTQ_()

        self.ast._define(
            ['path', 'arglist'],
            ['set']
        )

    @graken()
    def _callargs_(self):
        self._token('(')
        with self._optional():
            self._expr_()
            self.ast.setlist('@', self.last_node)

            def block1():
                self._token(',')
                self._expr_()
                self.ast.setlist('@', self.last_node)
            self._closure(block1)
            with self._optional():
                self._token(',')
        self._token(')')

    @graken()
    def _top_(self):
        self._token('{')

        def block0():
            self._set_()
            self.ast.setlist('set', self.last_node)
            with self._optional():
                self._COMMENTSB_()
            self._token(';')
        self._closure(block0)
        with self._group():
            with self._choice():
                with self._option():
                    self._set_()
                    self.ast.setlist('set', self.last_node)
                with self._option():
                    with self._group():

                        def block3():
                            self._expr_()
                            self.ast.setlist('exprs', self.last_node)
                            self._token(';')
                        self._closure(block3)
                        with self._optional():
                            self._topemitexpr_()
                            self.ast['emit'] = self.last_node
                self._error('no available options')
        with self._optional():
            self._commentb_()
            self.ast['commentb'] = self.last_node
        pass
        self.ast['dummy'] = self.last_node
        self._token('}')

        self.ast._define(
            ['emit', 'commentb', 'dummy'],
            ['set', 'exprs']
        )

    @graken()
    def _commentb_(self):
        self._COMMENTB_()

    @graken()
    def _set_(self):
        with self._choice():
            with self._option():
                self._lset_()
            with self._option():
                self._setif_()
            self._error('no available options')

    @graken()
    def _lset_(self):
        self._lvar_()
        self.ast['lvar'] = self.last_node
        self._token('=')
        self._expr_()
        self.ast['expr'] = self.last_node

        self.ast._define(
            ['lvar', 'expr'],
            []
        )

    @graken()
    def _lvar_(self):
        self._name_()

    @graken()
    def _setif_(self):
        self._name_()
        self.ast['var'] = self.last_node
        with self._group():
            with self._choice():
                with self._option():
                    self._token('=?')
                with self._option():
                    self._token('?=')
                self._error('expecting one of: =? ?=')
        self._expr_()
        self.ast['expr'] = self.last_node

        self.ast._define(
            ['var', 'expr'],
            []
        )

    @graken()
    def _topemitexpr_(self):
        with self._choice():
            with self._option():
                self._placeholder_()
            with self._option():
                self._filtexp_()
            self._error('no available options')

    @graken()
    def _placeholder_(self):
        with self._group():
            with self._choice():
                with self._option():
                    self._token('*')
                with self._option():
                    self._token('++')
                self._error('expecting one of: * ++')
        self.ast['@'] = self.last_node
        self._token(':')
        self._name_()
        self.ast['@'] = self.last_node

    @graken()
    def _filtexp_(self):
        self._expr_()
        self.ast['expr'] = self.last_node

        def block1():
            self._filter_()
            self.ast.setlist('filter', self.last_node)
        self._closure(block1)

        self.ast._define(
            ['expr'],
            ['filter']
        )

    @graken()
    def _filter_(self):
        self._token('|')
        with self._group():
            with self._choice():
                with self._option():
                    self._call_()
                    self.ast['@'] = self.last_node
                with self._option():
                    self._path_()
                    self.ast['@'] = self.last_node
                self._error('no available options')

    @graken()
    def _expr_(self):
        with self._choice():
            with self._option():
                self._ternary_()
            with self._option():
                self._range_()
            with self._option():
                self._simpleexpr_()
            self._error('no available options')

    @graken()
    def _ternary_(self):
        self._test_()
        self.ast['test'] = self.last_node
        with self._group():
            self._token('?')
            with self._optional():
                self._expr_()
                self.ast['true'] = self.last_node
            with self._optional():
                self._token(':')
                self._expr_()
                self.ast['false'] = self.last_node

        self.ast._define(
            ['test', 'true', 'false'],
            []
        )

    @graken()
    def _test_(self):
        with self._choice():
            with self._option():
                self._regex_()
            with self._option():
                self._comp_()
            self._error('no available options')

    @graken()
    def _regex_(self):
        self._simpleexpr_()
        self.ast['expr'] = self.last_node
        with self._group():
            with self._choice():
                with self._option():
                    self._token('~!')
                with self._option():
                    self._token('!~')
                with self._option():
                    self._token('~')
                self._error('expecting one of: !~ ~ ~!')
        self.ast['op'] = self.last_node
        self._relit_()
        self.ast['re'] = self.last_node

        self.ast._define(
            ['expr', 'op', 're'],
            []
        )

    @graken()
    def _relit_(self):
        self._REGEX_()

    @graken()
    def _comp_(self):
        self._simpleexpr_()
        self.ast.setlist('@', self.last_node)
        with self._group():
            with self._choice():
                with self._option():

                    def block1():
                        self._compop_()
                        self.ast.setlist('@', self.last_node)
                        self._simpleexpr_()
                        self.ast.setlist('@', self.last_node)
                    self._positive_closure(block1)
                with self._option():
                    with self._optional():
                        self._eqop_()
                        self.ast.setlist('@', self.last_node)
                        self._simpleexpr_()
                        self.ast.setlist('@', self.last_node)
                self._error('no available options')

    @graken()
    def _eqop_(self):
        with self._choice():
            with self._option():
                self._token('==')
            with self._option():
                self._token('!=')
            with self._option():
                self._token('eq')
            with self._option():
                self._token('ne')
            self._error('expecting one of: != == eq ne')

    @graken()
    def _compop_(self):
        with self._choice():
            with self._option():
                self._token('le')
            with self._option():
                self._token('ge')
            with self._option():
                self._token('gt')
            with self._option():
                self._token('lt')
            with self._option():
                self._token('<=')
            with self._option():
                self._token('=<')
            with self._option():
                self._token('<')
            with self._option():
                self._token('>=')
            with self._option():
                self._token('=>')
            with self._option():
                self._token('>')
            self._error('expecting one of: < <= =< => > >= ge gt le lt')

    @graken()
    def _range_(self):
        self._simpleexpr_()
        with self._group():
            with self._choice():
                with self._option():
                    self._token('...')
                with self._option():
                    self._token('..')
                self._error('expecting one of: .. ...')
        self._simpleexpr_()

    @graken()
    def _simpleexpr_(self):
        with self._choice():
            with self._option():
                self._call_()
            with self._option():
                self._path_()
            with self._option():
                self._value_()
            with self._option():
                self._list_()
            with self._option():
                self._map_()
            self._error('no available options')

    @graken()
    def _call_(self):
        self._path_()
        self.ast['fn'] = self.last_node
        self._token('(')
        with self._optional():
            self._expr_()
            self.ast.setlist('arg', self.last_node)

            def block2():
                self._token(',')
                self._expr_()
                self.ast.setlist('arg', self.last_node)
            self._closure(block2)
            with self._optional():
                self._token(',')
        self._token(')')

        self.ast._define(
            ['fn'],
            ['arg']
        )

    @graken()
    def _path_(self):
        with self._group():
            with self._choice():
                with self._option():
                    self._externalPath_()
                with self._option():
                    self._dotPath_()
                with self._option():
                    self._dottedPath_()
                self._error('no available options')
        self.ast['path'] = self.last_node
        with self._optional():
            self._lookup_()
        self.ast['lookup'] = self.last_node

        self.ast._define(
            ['path', 'lookup'],
            []
        )

    @graken()
    def _dottedPath_(self):
        self._pname_()
        self.ast.setlist('@', self.last_node)

        def block1():
            self._token('.')
            self._pname_()
            self.ast.setlist('@', self.last_node)
        self._closure(block1)

    @graken()
    def _dotPath_(self):
        self._token('.')
        self.ast.setlist('@', self.last_node)
        with self._optional():
            self._pname_()
            self.ast.setlist('@', self.last_node)

            def block2():
                self._token('.')
                self._pname_()
                self.ast.setlist('@', self.last_node)
            self._closure(block2)

    @graken()
    def _externalPath_(self):
        self._pname_()
        self.ast['module'] = self.last_node
        self._token('::')
        self._pname_()
        self.ast.setlist('path', self.last_node)

        def block2():
            self._token('.')
            self._pname_()
            self.ast.setlist('path', self.last_node)
        self._closure(block2)

        self.ast._define(
            ['module'],
            ['path']
        )

    @graken()
    def _pname_(self):
        self._NAME_()

    @graken()
    def _lookup_(self):
        self._token('[')
        self._simpleexpr_()
        self.ast['@'] = self.last_node
        self._token(']')

    @graken()
    def _value_(self):
        with self._choice():
            with self._option():
                self._number_()
            with self._option():
                self._string_()
            self._error('no available options')

    @graken()
    def _number_(self):
        self._NUMBER_()

    @graken()
    def _string_(self):
        self._STRING_()

    @graken()
    def _list_(self):
        self._token('[')
        with self._optional():
            with self._group():
                with self._choice():
                    with self._option():
                        self._expr_()
                    with self._option():
                        self._starexp_()
                    self._error('no available options')
            self.ast.setlist('@', self.last_node)

            def block2():
                self._token(',')
                with self._group():
                    with self._choice():
                        with self._option():
                            self._expr_()
                        with self._option():
                            self._starexp_()
                        self._error('no available options')
                self.ast.setlist('@', self.last_node)
            self._closure(block2)
            with self._optional():
                self._token(',')
        self._token(']')

    @graken()
    def _starexp_(self):
        self._token('*')
        self._expr_()
        self.ast['@'] = self.last_node

    @graken()
    def _map_(self):
        self._token('{')
        with self._optional():
            with self._group():
                with self._choice():
                    with self._option():
                        self._member_()
                    with self._option():
                        self._starexp_()
                    self._error('no available options')
            self.ast.setlist('@', self.last_node)

            def block2():
                self._token(',')
                with self._group():
                    with self._choice():
                        with self._option():
                            self._member_()
                        with self._option():
                            self._starexp_()
                        self._error('no available options')
                self.ast.setlist('@', self.last_node)
            self._closure(block2)
        self._token('}')

    @graken()
    def _member_(self):
        with self._group():
            with self._choice():
                with self._option():
                    self._number_()
                with self._option():
                    self._string_()
                with self._option():
                    self._barename_()
                self._error('no available options')
        self.ast['key'] = self.last_node
        self._token(':')
        self._expr_()
        self.ast['val'] = self.last_node

        self.ast._define(
            ['key', 'val'],
            []
        )

    @graken()
    def _barename_(self):
        self._name_()

    @graken()
    def _COMMENTQ_(self):
        self._pattern(r'#[^"]*')

    @graken()
    def _COMMENTSQ_(self):
        self._pattern(r'#[^";]*')

    @graken()
    def _COMMENTB_(self):
        self._pattern(r'#[^}]*')

    @graken()
    def _COMMENTSB_(self):
        self._pattern(r'#[^};]*')

    @graken()
    def _NAME_(self):
        self._pattern(r'[a-zA-Z][a-zA-Z0-9_]*')

    @graken()
    def _REGEX_(self):
        self._pattern(r'[/].*?[/]')

    @graken()
    def _INT_(self):
        self._pattern(r'[0-9]+')

    @graken()
    def _DOT_(self):
        self._token('.')

    @graken()
    def _DOTS_(self):
        with self._choice():
            with self._option():
                self._DOT_()
            with self._option():
                self._token('.')

                def block0():
                    self._token('.')
                self._positive_closure(block0)
            self._error('expecting one of: .')

    @graken()
    def _NUMBER_(self):
        self._pattern(r'-?[0-9]+([.][0-9]+([eE][+-]?[0-9]+)?)?')

    @graken()
    def _WS_(self):
        with self._group():
            with self._choice():
                with self._option():
                    self._token(' ')
                with self._option():
                    self._token('\t')
                self._error('expecting one of: \t  ')

    @graken()
    def _NL_(self):
        with self._choice():
            with self._option():
                self._token('\n')
            with self._option():
                self._token('\r')
            self._error('expecting one of: \n \r')

    @graken()
    def _STRING_(self):
        self._pattern(r'([\'"]).*?\1')

    @graken()
    def _PYEXPR_(self):
        self._token('(')
        self._O_()
        with self._optional():
            self._PYEXPR_()
        self._O_()
        self._token(')')

    @graken()
    def _O_(self):
        self._pattern(r'[^()]*')


class ExprSemantics(object):
    def defAttr(self, ast):
        return ast

    def forAttr(self, ast):
        return ast

    def ifAttr(self, ast):
        return ast

    def paramAttr(self, ast):
        return ast

    def setAttr(self, ast):
        return ast

    def useAttr(self, ast):
        return ast

    def attrs(self, ast):
        return ast

    def defExpr(self, ast):
        return ast

    def arglist(self, ast):
        return ast

    def arg(self, ast):
        return ast

    def name(self, ast):
        return ast

    def setExpr(self, ast):
        return ast

    def forExpr(self, ast):
        return ast

    def forpragma(self, ast):
        return ast

    def ifExpr(self, ast):
        return ast

    def paramExpr(self, ast):
        return ast

    def useExpr(self, ast):
        return ast

    def callargs(self, ast):
        return ast

    def top(self, ast):
        return ast

    def commentb(self, ast):
        return ast

    def set(self, ast):
        return ast

    def lset(self, ast):
        return ast

    def lvar(self, ast):
        return ast

    def setif(self, ast):
        return ast

    def topemitexpr(self, ast):
        return ast

    def placeholder(self, ast):
        return ast

    def filtexp(self, ast):
        return ast

    def filter(self, ast):
        return ast

    def expr(self, ast):
        return ast

    def ternary(self, ast):
        return ast

    def test(self, ast):
        return ast

    def regex(self, ast):
        return ast

    def relit(self, ast):
        return ast

    def comp(self, ast):
        return ast

    def eqop(self, ast):
        return ast

    def compop(self, ast):
        return ast

    def range(self, ast):
        return ast

    def simpleexpr(self, ast):
        return ast

    def call(self, ast):
        return ast

    def path(self, ast):
        return ast

    def dottedPath(self, ast):
        return ast

    def dotPath(self, ast):
        return ast

    def externalPath(self, ast):
        return ast

    def pname(self, ast):
        return ast

    def lookup(self, ast):
        return ast

    def value(self, ast):
        return ast

    def number(self, ast):
        return ast

    def string(self, ast):
        return ast

    def list(self, ast):
        return ast

    def starexp(self, ast):
        return ast

    def map(self, ast):
        return ast

    def member(self, ast):
        return ast

    def barename(self, ast):
        return ast

    def COMMENTQ(self, ast):
        return ast

    def COMMENTSQ(self, ast):
        return ast

    def COMMENTB(self, ast):
        return ast

    def COMMENTSB(self, ast):
        return ast

    def NAME(self, ast):
        return ast

    def REGEX(self, ast):
        return ast

    def INT(self, ast):
        return ast

    def DOT(self, ast):
        return ast

    def DOTS(self, ast):
        return ast

    def NUMBER(self, ast):
        return ast

    def WS(self, ast):
        return ast

    def NL(self, ast):
        return ast

    def STRING(self, ast):
        return ast

    def PYEXPR(self, ast):
        return ast

    def O(self, ast):
        return ast


def main(filename, startrule, trace=False, whitespace=None):
    import json
    with open(filename) as f:
        text = f.read()
    parser = ExprParser(parseinfo=False)
    ast = parser.parse(
        text,
        startrule,
        filename=filename,
        trace=trace,
        whitespace=whitespace)
    print('AST:')
    print(ast)
    print()
    print('JSON:')
    print(json.dumps(ast, indent=2))
    print()

if __name__ == '__main__':
    import argparse
    import string
    import sys

    class ListRules(argparse.Action):
        def __call__(self, parser, namespace, values, option_string):
            print('Rules:')
            for r in ExprParser.rule_list():
                print(r)
            print()
            sys.exit(0)

    parser = argparse.ArgumentParser(description="Simple parser for Expr.")
    parser.add_argument('-l', '--list', action=ListRules, nargs=0,
                        help="list all rules and exit")
    parser.add_argument('-t', '--trace', action='store_true',
                        help="output trace information")
    parser.add_argument('-w', '--whitespace', type=str, default=string.whitespace,
                        help="whitespace specification")
    parser.add_argument('file', metavar="FILE", help="the input file to parse")
    parser.add_argument('startrule', metavar="STARTRULE",
                        help="the start rule for parsing")
    args = parser.parse_args()

    main(
        args.file,
        args.startrule,
        trace=args.trace,
        whitespace=args.whitespace
    )
