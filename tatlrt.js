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
		if (incl) n--
		for (var i = m; i > n; i--) { l.push(i) }
	}
	return l
}

var _proto = {
	emit: function (s) {
		if (!s) this.qstack[0] = false
		this.cur.push(s) 
	},
	q: function q(s) {
		if (s == undefined || s == null) 
			return ''
		if (s instanceof Array) 
			return s.map(this.q).join(' ')
		if (typeof s == 'object')
			return JSON.stringify(s)
		return (''+s).replace(/[&<>"'\/]/g, function (c) { return ents[c] })
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
		return this.outs.join('')
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
			v = v[p]
		}
		return v
	},
	buildtag: function (tag, attrs) {
		return {tag: tag, attrs: attrs, content: this.pop(), __proto__: _tag}
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
	"/": '&#x2F;'
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

function forloop(obj, opts) {
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

function _wrap(fn) {
    return function (f) {
        return function () {
            return fn(f.call({}, arguments))
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
function trim(s) {return s.trim()}
exports.exprfilt = {
	trim: trim,
}
exports.callfilt = {
	trim: _wrap(trim),
}
