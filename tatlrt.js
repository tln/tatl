exports._ctx = function(quotestyle) {
	var cur = []
	return {
		outs: [cur],
		cur: cur,
		qstack: [],
		__proto__: _proto
	}
}
exports._bind = function(f) {
	// compiled macros use func.call to emulate Python's **kw
	// We don't want to pick up the "this" from structures constructed 
	// later...
	var f2 = f.bind({})
	f2.call = f.call.bind(f)
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

var _proto = {
	emit: function (s) {
		if (!s) this.qstack[0] = false
		this.cur.push(s) 
	},
	q: function q(s) {
		if (s == undefined || s == null) 
			return ''
		if (s.__safe__)
			return s
		if (s instanceof Array) 
			return s.map(this.q).join(' ')
		if (typeof s == 'object' && !(s instanceof String))
			return JSON.stringify(s)
		return (''+s).replace(/[&<>"']/g, function (c) { return ents[c] })
    },
	push: function () { 
		this.outs.push(this.cur = []) 
	},
	pop: function ()  { 
		this.cur = this.outs[this.outs.length-2]
		return this.outs.pop().join('') 
	},
	result: function () { 
		for (var i = 0; i < this.outs.length; i++) {
			this.outs[i] = this.outs[i].join('')
		}
		return exports.safe(this.outs.join(''))
	},
	elidestart: function () {
		this.push()
		this.qstack.unshift(true)
	},
	elidecheck: function () {
		return this.qstack.shift()
	},
	get1: function (v, path) {
		return v == undefined || v == null ? v : v[path]
	},
	get: function (v, paths) {
		for (p in paths) {
			if (v == undefined || v == null) break
			v = v[paths[p]]
		}
		return v
	},
	buildtag: function (tag, attrs) {
		return {tag: tag, attrs: attrs, content: this.pop(), __proto__: _tag}
	},
	load: function (module, paths) {
		return this.get(require('./tests/out/'+module), paths)
	}
}
var _tag = {
	// no behavior (yet)
}
var ents = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	'"': '&quot;',
	"'": '&#39;',
};
_forloop = {
	cycle: [],
	firstclass: 'first',
	lastclass: 'last', 
	preclass: '', 
	postclass: '',
	pre: false,
	post: false,
	
	class_: function () {
        var l = []
        if (this.preclass && this.pre)
            l.push(this.preclass)
        if (this.firstclass && this.first)
            l.push(this.firstclass)
        if (this.cycle)
            l.push(this.cycle[this.counter0 % this.cycle.length])
        if (this.lastclass && this.last)
            l.push(this.lastclass)
        if (this.postclass && this.post)
            l.push(this.postclass)
        return l.join(' ')
	}
}

exports.forloop = function (obj, opts) {
	var r = []
	opts = opts || {}
	opts.__proto__ = _forloop
	if (opts.preclass) {
		r.push({pre: true, __proto__: opts})
	}
	if (typeof obj.length == 'undefined') {
		var last, i = 0;
		for (var key in obj) {
			r.push(last = {
				first: i == 0,
				last: false,
				counter0: i,
				counter: i+1,
				key: c,
				value: obj[c],
				__proto__: opts,
			});
			i++;
		}
		last.last = true
	} else {
		for (var i = 0; i < obj.length; i++) {
			r.push({
				counter0: i,
				counter: i+1,
				value: obj[i],
				first: i == 0,
				last: i == obj.length-1,
			})
		}
	}
	if (opts.postclass) {
		r.push({post: true, __proto__: opts})
	}
	return r
}

exports.wrap = function (fn) {
    return function (f) {
        return function () {
            return fn(f.apply({}, arguments))
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

exports.trim = function (s) {
	return s.trim()
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
    return fn(s, start, m)
}

exports.contents = function (s) {
    return _findtag(s, function (s, start, end) { 
		return s.slice(start[1].length, end.index) 
	})
}

exports.tag = function (newtag, s) {
    return _findtag(s, function (s, start, end) { 
        return start[1] + newtag + start[3] 
			+ s.slice(start[0].length, end.index+2) + newtag + s.substring(end.index+end[0].length)
    })
}

// to facilitate internal quoting
var _attr = exports._ctx('attr')
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
