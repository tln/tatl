var tatlrt = require('tatlrt');
_forloop = {
	cycle: [],
	firstclass: 'first',
	lastclass: 'last',
	preclass: '',
	postclass: '',
	pre: false,
	post: false,

	classes: function () {
        debugger;
        var l = []
        if (this.preclass && this.pre)
            l.push(this.preclass)
        if (this.firstclass && this.first)
            l.push(this.firstclass)
        if (this.cycle.length)
            l.push(this.cycle[this.counter0 % this.cycle.length])
        if (this.lastclass && this.last)
            l.push(this.lastclass)
        if (this.postclass && this.post)
            l.push(this.postclass)
        return l.join(' ')
	},

    _updtotals: function (r) {
        // Called on total row.
        // Update this.value based on preceding rows and any aggregators defined
        // in this.total; return whether to include this total object in result set
        var includerow = this.postclass
        if (this.total) {
            var values = []
            for (var i = r.length && r[0].pre?1:0; i < r.length; i++) {
                values.push(r[i].value)
            }
            debugger;
            if (this.total instanceof Function) {
                this.value = this.total(values)
            } else {
                this.value = {}
                for (var key in this.total) {
                    var val = this.total[key]
                    if (val instanceof Function) {
                        val = val(values.map(function (x){return x[key]}))
                    }
                    this.value[key] = val
                }
            }
            includerow = true
        }
        if (this.totalkey) {
            this.key = this.totalkey
            includerow = true
        }
        return includerow
    }
}
exports.sum = function (values) {
    debugger;
    var result = 0
    for (var k in values) {
        var v = values[k]
        if (typeof v != 'number') return null
        result += v
    }
    return result
}
exports.forloop = function (obj, opts) {
	var r = [], last = {}, cur, i = 0, keys = tatlrt.keys(obj)
	opts = opts || {}
	opts.__proto__ = _forloop
    total = {post: true, __proto__: opts}
	if (opts.preclass) {
		r.push(last = {pre: true, __proto__: opts})
	}
	for (var key; key = keys[i], i < keys.length; i++) {
		r.push(cur = {
			counter0: i,
			counter: i+1,
            key: key,
			value: obj[key],
			first: i == 0,
			last: i == keys.length-1,
            prev: last,
            __proto__: opts
		})
        last = last.next = cur;
	}
    if (r.length) r[0].prev = null
	if (total._updtotals(r)) {
		r.push(last.next = total)
	}
	return r
}
