#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# CAVEAT UTILITOR
# This file was automatically generated by Grako.
#    https://bitbucket.org/apalala/grako/
# Any changes you make to it will be overwritten the
# next time the file is generated.
#

from __future__ import print_function, division, absolute_import, unicode_literals
from grako.parsing import * # @UnusedWildImport
from grako.exceptions import * # @UnusedWildImport

__version__ = '14.045.20.39.02'

class ExprParser(Parser):
    def __init__(self, whitespace=None, nameguard=True, **kwargs):
        super(ExprParser, self).__init__(whitespace=whitespace,
            nameguard=nameguard, **kwargs)

    @rule_def
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
                self._token('"')
            with self._option():
                self._top_()
            self._error('no available options')

    @rule_def
    def _defExpr_(self):
        self._NAME_()
        self.ast['name'] = self.last_node
        self._arglist_()
        self.ast['args'] = self.last_node
        def block2():
            self._filter_()
            self.ast.add_list('filter', self.last_node)
        self._closure(block2)
        with self._optional():
            self._token('=')
            self._expr_()
            self.ast['result'] = self.last_node

    @rule_def
    def _setExpr_(self):
        self._set_()
        self.ast.add_list('set', self.last_node)
        def block1():
            self._token(';')
            self._set_()
            self.ast.add_list('set', self.last_node)
        self._closure(block1)

    @rule_def
    def _arglist_(self):
        self._token('(')
        with self._optional():
            self._arg_()
            self.ast.add_list('@', self.last_node)
            def block1():
                self._token(',')
                self._arg_()
                self.ast.add_list('@', self.last_node)
            self._closure(block1)
            with self._optional():
                self._token(',')
        self._token(')')

    @rule_def
    def _arg_(self):
        with self._choice():
            with self._option():
                self._NAME_()
                self.ast['@'] = self.last_node
            with self._option():
                self._token('*')
                self.ast['@'] = self.last_node
            self._error('expecting one of: *')

    @rule_def
    def _forExpr_(self):
        def block0():
            self._set_()
            self.ast.add_list('set', self.last_node)
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

    @rule_def
    def _ifExpr_(self):
        def block0():
            self._set_()
            self.ast.add_list('set', self.last_node)
            self._token(';')
        self._closure(block0)
        self._test_()
        self.ast['@'] = self.last_node

    @rule_def
    def _paramExpr_(self):
        self._lvar_()
        self.ast.add_list('@', self.last_node)
        def block1():
            self._token(',')
            self._lvar_()
            self.ast.add_list('@', self.last_node)
        self._closure(block1)

    @rule_def
    def _useExpr_(self):
        def block0():
            self._set_()
            self.ast.add_list('set', self.last_node)
            self._token(';')
        self._closure(block0)
        self._path_()
        self.ast['path'] = self.last_node
        with self._optional():
            self._callargs_()
            self.ast['arglist'] = self.last_node

    @rule_def
    def _callargs_(self):
        self._token('(')
        with self._optional():
            self._expr_()
            def block0():
                self._token(',')
                self._expr_()
            self._closure(block0)
            with self._optional():
                self._token(',')
        self._token(')')

    @rule_def
    def _top_(self):
        self._token('{')
        def block0():
            self._set_()
            self.ast.add_list('set', self.last_node)
            self._token(';')
        self._closure(block0)
        with self._group():
            with self._choice():
                with self._option():
                    self._set_()
                    self.ast.add_list('set', self.last_node)
                with self._option():
                    with self._group():
                        def block3():
                            self._expr_()
                            self.ast.add_list('exprs', self.last_node)
                            self._token(';')
                        self._closure(block3)
                        with self._optional():
                            self._topemitexpr_()
                            self.ast['emit'] = self.last_node
                self._error('no available options')
        self._token('}')

    @rule_def
    def _set_(self):
        self._lvar_()
        self.ast['lvar'] = self.last_node
        with self._group():
            with self._choice():
                with self._option():
                    self._token('=')
                with self._option():
                    self._token('=?')
                with self._option():
                    self._token('?=')
                self._error('expecting one of: =? ?= =')
        self.ast['op'] = self.last_node
        self._expr_()
        self.ast['expr'] = self.last_node

    @rule_def
    def _lvar_(self):
        self._NAME_()

    @rule_def
    def _topemitexpr_(self):
        with self._choice():
            with self._option():
                self._starexp_()
                self.ast['star'] = self.last_node
            with self._option():
                self._filtexp_()
                self.ast['filtexp'] = self.last_node
            self._error('no available options')

    @rule_def
    def _filtexp_(self):
        self._expr_()
        self.ast['expr'] = self.last_node
        def block1():
            self._filter_()
            self.ast.add_list('filter', self.last_node)
        self._closure(block1)

    @rule_def
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
                with self._option():
                    self._string_()
                    self.ast['@'] = self.last_node
                self._error('no available options')

    @rule_def
    def _starexp_(self):
        with self._choice():
            with self._option():
                with self._group():
                    with self._choice():
                        with self._option():
                            self._token('*')
                        with self._option():
                            self._token('++')
                        self._error('expecting one of: ++ *')
                self.ast['@'] = self.last_node
                self._token(':')
                self._NAME_()
                self.ast['@'] = self.last_node
            with self._option():
                self._token('*')
                self._expr_()
            self._error('no available options')

    @rule_def
    def _expr_(self):
        with self._choice():
            with self._option():
                self._ternary_()
            with self._option():
                self._range_()
            with self._option():
                self._simpleexpr_()
            self._error('no available options')

    @rule_def
    def _ternary_(self):
        self._test_()
        self.ast['test'] = self.last_node
        with self._group():
            with self._choice():
                with self._option():
                    self._token('?')
                    self._expr_()
                    self.ast['true'] = self.last_node
                    with self._optional():
                        self._token(':')
                        self._expr_()
                        self.ast['false'] = self.last_node
                with self._option():
                    self._token('?:')
                    self._expr_()
                    self.ast['false'] = self.last_node
                self._error('no available options')

    @rule_def
    def _test_(self):
        with self._choice():
            with self._option():
                self._regex_()
            with self._option():
                self._comp_()
            self._error('no available options')

    @rule_def
    def _regex_(self):
        self._simpleexpr_()
        self.ast['expr'] = self.last_node
        with self._group():
            with self._choice():
                with self._option():
                    self._token('~')
                with self._option():
                    self._token('!~')
                with self._option():
                    self._token('~!')
                self._error('expecting one of: ~ !~ ~!')
        self.ast['op'] = self.last_node
        self._REGEX_()
        self.ast['re'] = self.last_node

    @rule_def
    def _comp_(self):
        self._simpleexpr_()
        self.ast.add_list('@', self.last_node)
        with self._group():
            with self._choice():
                with self._option():
                    def block1():
                        self._compop_()
                        self.ast.add_list('@', self.last_node)
                        self._simpleexpr_()
                        self.ast.add_list('@', self.last_node)
                    self._positive_closure(block1)
                with self._option():
                    with self._optional():
                        self._eqop_()
                        self.ast.add_list('@', self.last_node)
                        self._simpleexpr_()
                        self.ast.add_list('@', self.last_node)
                self._error('no available options')

    @rule_def
    def _eqop_(self):
        with self._choice():
            with self._option():
                self._token('==')
            with self._option():
                self._token('!=')
            self._error('expecting one of: == !=')

    @rule_def
    def _compop_(self):
        with self._choice():
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
            self._error('expecting one of: > >= => <= < =<')

    @rule_def
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

    @rule_def
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

    @rule_def
    def _call_(self):
        self._path_()
        self.ast['fn'] = self.last_node
        self._token('(')
        with self._optional():
            self._expr_()
            self.ast.add_list('arg', self.last_node)
            def block2():
                self._token(',')
                self._expr_()
                self.ast.add_list('arg', self.last_node)
            self._closure(block2)
            with self._optional():
                self._token(',')
        self._token(')')

    @rule_def
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

    @rule_def
    def _dottedPath_(self):
        self._NAME_()
        self.ast.add_list('@', self.last_node)
        def block1():
            self._token('.')
            self._NAME_()
            self.ast.add_list('@', self.last_node)
        self._closure(block1)

    @rule_def
    def _dotPath_(self):
        self._token('.')
        self.ast.add_list('@', self.last_node)
        with self._optional():
            self._NAME_()
            self.ast.add_list('@', self.last_node)
            def block2():
                self._token('.')
                self._NAME_()
                self.ast.add_list('@', self.last_node)
            self._closure(block2)

    @rule_def
    def _externalPath_(self):
        self._NAME_()
        self.ast['module'] = self.last_node
        self._token('::')
        self._NAME_()
        self.ast.add_list('path', self.last_node)
        def block2():
            self._token('.')
            self._NAME_()
            self.ast.add_list('path', self.last_node)
        self._closure(block2)

    @rule_def
    def _lookup_(self):
        self._token('[')
        self._simpleexpr_()
        self.ast['@'] = self.last_node
        self._token(']')

    @rule_def
    def _value_(self):
        with self._choice():
            with self._option():
                self._number_()
            with self._option():
                self._string_()
            self._error('no available options')

    @rule_def
    def _number_(self):
        self._NUMBER_()

    @rule_def
    def _string_(self):
        self._STRING_()

    @rule_def
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
            self.ast.add_list('@', self.last_node)
            def block2():
                self._token(',')
                with self._group():
                    with self._choice():
                        with self._option():
                            self._expr_()
                        with self._option():
                            self._starexp_()
                        self._error('no available options')
                self.ast.add_list('@', self.last_node)
            self._closure(block2)
            with self._optional():
                self._token(',')
        self._token(']')

    @rule_def
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
            self.ast.add_list('@', self.last_node)
            def block2():
                self._token(',')
                with self._group():
                    with self._choice():
                        with self._option():
                            self._member_()
                        with self._option():
                            self._starexp_()
                        self._error('no available options')
                self.ast.add_list('@', self.last_node)
            self._closure(block2)
        self._token('}')

    @rule_def
    def _member_(self):
        with self._group():
            with self._choice():
                with self._option():
                    self._NAME_()
                    self.ast['nkey'] = self.last_node
                with self._option():
                    self._STRING_()
                    self.ast['skey'] = self.last_node
                self._error('no available options')
        self._token(':')
        self._expr_()
        self.ast['val'] = self.last_node

    @rule_def
    def _REGEX_(self):
        self._pattern(r'[/].*?[/]')

    @rule_def
    def _NAME_(self):
        self._pattern(r'[a-zA-Z_][a-zA-Z0-9_]*')

    @rule_def
    def _INT_(self):
        self._pattern(r'[0-9]+')

    @rule_def
    def _DOT_(self):
        self._token('.')

    @rule_def
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

    @rule_def
    def _NUMBER_(self):
        self._pattern(r'-?[0-9]+([.][0-9]+([eE][+-]?[0-9]+)?)?')

    @rule_def
    def _WS_(self):
        with self._group():
            with self._choice():
                with self._option():
                    self._token(' ')
                with self._option():
                    self._token('\t')
                self._error('expecting one of: \t  ')

    @rule_def
    def _NL_(self):
        with self._choice():
            with self._option():
                self._token('\n')
            with self._option():
                self._token('\r')
            self._error('expecting one of: \n \r')

    @rule_def
    def _STRING_(self):
        self._pattern(r'([\'"]).*?\1')

    @rule_def
    def _PYEXPR_(self):
        self._token('(')
        self._O_()
        with self._optional():
            self._PYEXPR_()
        self._O_()
        self._token(')')

    @rule_def
    def _O_(self):
        self._pattern(r'[^()]*')



class ExprSemanticParser(CheckSemanticsMixin, ExprParser):
    pass


class ExprSemantics(object):
    def attrs(self, ast):
        return ast

    def defExpr(self, ast):
        return ast

    def setExpr(self, ast):
        return ast

    def arglist(self, ast):
        return ast

    def arg(self, ast):
        return ast

    def forExpr(self, ast):
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

    def set(self, ast):
        return ast

    def lvar(self, ast):
        return ast

    def topemitexpr(self, ast):
        return ast

    def filtexp(self, ast):
        return ast

    def filter(self, ast):
        return ast

    def starexp(self, ast):
        return ast

    def expr(self, ast):
        return ast

    def ternary(self, ast):
        return ast

    def test(self, ast):
        return ast

    def regex(self, ast):
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

    def map(self, ast):
        return ast

    def member(self, ast):
        return ast

    def REGEX(self, ast):
        return ast

    def NAME(self, ast):
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

def main(filename, startrule, trace=False):
    import json
    with open(filename) as f:
        text = f.read()
    parser = ExprParser(parseinfo=False)
    ast = parser.parse(text, startrule, filename=filename, trace=trace)
    print('AST:')
    print(ast)
    print()
    print('JSON:')
    print(json.dumps(ast, indent=2))
    print()

if __name__ == '__main__':
    import argparse
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
    parser.add_argument('file', metavar="FILE", help="the input file to parse")
    parser.add_argument('startrule', metavar="STARTRULE",
                        help="the start rule for parsing")
    args = parser.parse_args()

    main(args.file, args.startrule, trace=args.trace)
