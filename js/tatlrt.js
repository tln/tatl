exports.templates = {};
exports.add_template = function (modname, template_exports) {
    exports.templates._last = modname;
    exports.templates[modname] = template_exports;
}
exports.last = function () {
    return exports.templates[exports.templates._last];
}
exports.ctx = function(quotestyle) {
	var cur = []
	return {
		outs: [cur],
		cur: cur,
		qstack: [true],
		__proto__: _proto
	}
}
exports._bind = function(f) {
	// compiled macros use func.call to emulate Python's **kw
	// We don't want to pick up the "this" from structures constructed
	// later...
	var f2 = f.bind({})
	f2.call = f.call.bind(f)
    f2.orig = f
	return f2
}
exports.range = function (n,m,incl) {
	var l = []
	if (n < m) {
		if (incl) m++
		for (var i = n; i < m; i++) { l.push(i) }
	} else {
		if (!incl) n--
		for (var i = n; i >= m; i--) { l.push(i) }
	}
	return l
}

exports.safe = function (s) {
	s = new String(s)
	s.__safe__ = true
	return s
}

function keys(object, unsorted) {
    if (object === null || object === undefined) {
        return []
    }
    if (object.length !== undefined) {
        return exports.range(0, object.length, false)
    } else {
        var l = []
        for (k in object) l.push(k)
        if (!unsorted) l.sort()
        return l
    }
}
exports.keys = keys;

var _proto = {
	emit: function (s) {
		this.cur.push(s)
	},
    u: function u(s) {
        if (s === '') return '';
        if (s === 0) return '0';
		if (!s) {
			this.qstack[0] = false
            return '';
        }
        return s+'';
    },
	q: function q(s) {
        if (s === '') return ''
        if (s === 0) return '0'
		if (!s) {
			this.qstack[0] = false
            return ''
        }
		if (s.__safe__)
			return s
		if (s instanceof Array)
			return s.map(this.q).join(' ')
		if (typeof s == 'object' && !(s instanceof String))
			return JSON.stringify(s)
		return (''+s).replace(/[&<>"']/g, function (c) { return ents[c] })
    },
	elidestart: function () {
		this.qstack.unshift(true)
	},
	elidecheck: function () {
		return this.qstack.shift()
	},
	get1: function (v, path) {
		if (v == undefined || v == null) return v
        if (v[path] instanceof Function) return v[path].bind(v)
        return v[path]
	},
	get: function (v, paths) {
		for (p in paths) {
			if (v == undefined || v == null) break
			v = v[paths[p]]
		}
		return v
	},
	load: function (module, paths) {
		return this.get(require('./tests/out/'+module), paths)
	},
    iter: function (obj) {
        if (obj === null || obj === undefined || obj === '') {
            return []
        } else if (obj.length !== undefined) {
            return obj
        } else if (typeof object == 'string' || object instanceof String) {
            return [obj]
        } else {
            return _.keys(obj)
        }
    },
    keys: keys,
    keysUnsorted: function (object) { return keys(object, true); },
    search: function (regex, object) {
        if (typeof object == 'string' || object instanceof String) {
            return regex.test(object)
        }
        return false
    },
    applyargs: function (self, func) {
        var rest = Array.prototype.slice.call(arguments, 2)
        return func.apply(self, rest)
    },
    applyautoexpr: function (name, func) {
        // determine func argument names
        // return expression where all func argument names are passed
        // avoid ReferenceErrors -- use "typeof VAR == 'undefined' ? undefined : VAR"
        // caller will eval() the returned expression
        var func = func.orig || func; // Go past the function layer added by _bind
        var ARGUMENT_NAMES = /([^\s,]+)/g;
        var s = func.toString().replace(/(\/\/.*$|\/\*[\s\S]*?\*\/)/mg, '')
        var args = s.slice(s.indexOf('(')+1, s.indexOf(')')).match(ARGUMENT_NAMES) || []
        args = args.map(function f(arg) {
            return 'typeof '+arg+' == "undefined" ? undefined : '+arg
        })
        return name + '(' + args.join(',') + ')'
    }
}
var ents = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	'"': '&quot;',
	"'": '&#39;',
};

function wrap(fn) {
    // Wrap function so that it can be used as a function filter or as an expression function
    return function (f) {
        if (f instanceof Function) {
            return function () {
                return fn(f.apply({}, arguments))
            }
        } else {
            return fn.apply({}, arguments)
        }
    }
}

exports.bool = function (v) {
	// Coerce to true/false. lists, empty objects are false like python
	switch (typeof v) {
	case 'list':
		return v.length > 0;
	case 'object':
		if (v == null) return true;
		for (key in v) return true;
		return false;
	default:
		return !!v
	}
}

url = wrap(function (s) { return encodeURIComponent(s) })

exports.filters = {
    trim: wrap(function (s) { return s.trim() }),
    url: url, u: url,
}

var TAG = /(\s*<)([a-zA-Z0-9_.:-]+)((.|\n)*?>)/
function _findtag(s, fn) {
    start = m = TAG.exec(s)
    if (!m || m.index > 0) return s
    count = 1
    p = new RegExp('<(/?)'+start[2]+'\s*', 'g')
	p.lastIndex = start[0].length
    while (count) {
        m = p.exec(s)
        if (!m) return s
        count += m[1] ? -1 : 1
	}
    if (s.substring(p.lastIndex+1).trim()) return s
    return exports.safe(fn(s, start, m))
}

exports.contents = function (s) {
    return _findtag(s, function (s, start, end) {
		return s.slice(start[0].length, end.index)
	})
}

exports.tag = function (tagname, attrs, inner) {
    if (inner === undefined) {
        inner = attrs;
        attrs = {}
    }
	var attstr = ''
	for (var k in attrs || {}) {
		attstr += ' '+k+'="'+_attr.q(attrs[k])+'"'
	}
    return exports.safe('<'+tagname+attstr+'>'+_attr.q(inner)+'</'+tagname+'>')
}

var _attr = exports.ctx('attr')     // to facilitate internal quoting

exports.attrs = function (attdict, s) {
    return _findtag(s, function (s, start, end) {
		var attstr = ''
		for (var k in attdict) {
			attstr += ' '+k+'="'+_attr.q(attdict[k])+'"'
		}
		var st = start[1] + start[2]
        return st + attstr + s.substring(st.length)
	})
}

exports.len = function (obj) {
    return obj.length
};
