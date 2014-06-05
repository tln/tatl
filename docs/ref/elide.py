import tatlrt
def html(**_kw):
    _, _q, _emit = tatlrt._ctx('attr')
    # locals: inner
    _emit(u'<html><h1>Elide</h1>\n')
    _emit = _.push()
    _emit(u'\n   <p if>{expr}</p>\n')
    inner, _emit = _.pop()
    _emit(_.applyargs(_.load(u'builder', [u'highlight']), inner))
    _emit(u'\n<p>This special form of the <code>if</code> attribute will use the substitutions in the tag as the\nbasis for the condition, so that if any substitution is empty the whole tag will not appear.\n\n</p></html>')
    return _.result()
# end
