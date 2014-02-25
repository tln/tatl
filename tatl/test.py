from tatl import ExprParser, ExprSemantics
import os, sys, json

TESTS = 'grammar/test.txt'
EXPECT = 'grammar/test.expect.json'
RULE = 'attrs'

def test_grammar(update=0):
    parser = ExprParser.ExprParser(
        parseinfo=True,
        semantics=ExprSemantics.ExprSemantics()
    )
    if os.path.exists(EXPECT):
        expect = json.load(open(EXPECT))
    else:
        assert update, "Missing %s -- run in update mode (-u)" % EXPECT
        expect = {}
    updated = {}
    fail = 0
    for line in open(TESTS):
        line = line.rstrip()
        try:
            ast = parser.parse(line, rule_name=RULE)
            if hasattr(ast, 'out'):
                out = ast.out()
            else:
                out = repr(ast)
        except:
            print 'FAILURE:', line
            import traceback
            traceback.print_exc()
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
    if update and updated:
        with open(EXPECT, 'w') as f:
            json.dump(updated, f, indent=4, sort_keys=True)
        print "Wrote", EXPECT
    else:
        assert not fail, "%d failures" % fail

if __name__ == '__main__':
    print "Running tests... (pass -u to update)"
    import sys
    ExprSemantics.DEBUG = True
    try:
        test_grammar('-u' in sys.argv)
    except Exception, e:
        print e
        sys.exit(1)
    