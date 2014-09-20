#include <Python.h>
#include "structmember.h"

#ifdef DEBUG
#define DEBUGLOG(ARGS...) printf(ARGS)
#else
#define DEBUGLOG(ARGS...) do {} while (0)
#endif

// 16k, minus room for malloc overhead
#define BUFSIZE 16300
#define BUFLEN BUFSIZE/sizeof(Py_UNICODE)
#define NBUF 500
typedef struct {
    PyObject_HEAD
    /* Type-specific fields go here. */
    Py_UNICODE **bufs;
    Py_ssize_t nbuf;    /* number of buffers in use */
    Py_ssize_t nfree;   /* number of py_UNICODEs available in last buffer */
    Py_ssize_t maxbufs; /* size of bufs */
    int blank_flag;     /* a blank value was seen */
} fastbuf_BufObject;

#define BUF(o) ((fastbuf_BufObject*)o)
#define P(o) (o->bufs[o->nbuf-1] + BUFLEN - o->nfree)
#define BYTES(o) (o->nbuf * BUFSIZE - o->nfree * sizeof(Py_UNICODE))
#define LEN(o) (BYTES(o) / sizeof(Py_UNICODE))

PyObject* safe_class = NULL;

Py_UNICODE *buf_alloc(fastbuf_BufObject *buf)
{
    /* Only call when previous buffer is full. */

    /* Grow the bufs array if needed. */
    if (buf->nbuf == buf->maxbufs) {
        buf->maxbufs += NBUF;
        buf->bufs = PyMem_Realloc(buf->bufs, buf->maxbufs * sizeof(Py_UNICODE*));
        DEBUGLOG("realloc %p\n", buf->bufs);
    }
    buf->nfree = BUFLEN;
    void* p = buf->bufs[buf->nbuf++] = PyMem_Malloc(BUFSIZE);
    DEBUGLOG("malloc %p\n", p);
    return p; // caller must detect error
}

PyObject* buf_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
PyObject* buf_str(fastbuf_BufObject* obj);
PyObject* buf_inplace_add(fastbuf_BufObject* obj, PyObject* other);

PyUnicodeObject *buf_other_to_unicode(PyObject* other, int* blank_flag)
{
    if (PyUnicode_Check(other)) {
        return (PyUnicodeObject *)other;
    }
    if (other == Py_None || other == Py_False) {
        *blank_flag = 1;
        return (PyUnicodeObject *)PyUnicode_FromString("");
    }
    if (other == Py_True) {
        return (PyUnicodeObject *)PyUnicode_FromString("true");
    }
    if (PyList_Check(other) || PyTuple_Check(other)) {
        fastbuf_BufObject* buf = (fastbuf_BufObject*)buf_new(NULL, NULL, NULL);
        PyObject* sp = PyUnicode_FromString(" ");
        for (int i = 0; i < PySequence_Length(other); i++) {
            if (i) buf_inplace_add(buf, sp);
            buf_inplace_add(buf, PySequence_GetItem(other, i));
        }
        return (PyUnicodeObject *)buf_str(buf);
    }
    if (PyFloat_Check(other)) {
        return (PyUnicodeObject*)PyNumber_Remainder(PyUnicode_FromString("%.16g"), other);
    }
    return (PyUnicodeObject *)PyObject_Unicode(other);
}

PyObject *
buf_inplace_add(fastbuf_BufObject* obj, PyObject* other)
{
    PyUnicodeObject *u = buf_other_to_unicode(other, &obj->blank_flag);
    Py_UNICODE *p = P(obj);
    Py_ssize_t n = 0;
    if (obj->nfree == 0) {
        p = buf_alloc(obj);
        if (!p) return PyErr_NoMemory();
    }
    while ((u->length - n) > obj->nfree) {
        memcpy(p, u->str + n, obj->nfree * sizeof(Py_UNICODE));
        n += obj->nfree;
        p = buf_alloc(obj);
        if (!p) return PyErr_NoMemory();
    }
    if (n < u->length) {
        memcpy(p, u->str + n, (u->length - n) * sizeof(Py_UNICODE));
        obj->nfree -= (u->length - n);
    }

    Py_INCREF(obj);
    return (PyObject *)obj;
}

static PyObject *
buf_inplace_and(fastbuf_BufObject* obj, PyObject* other)
{
    if (PyObject_Type(other) == safe_class) {
        /* No need to quote a safe instance */
        return buf_inplace_add(obj, other);
    }
    PyUnicodeObject *u = buf_other_to_unicode(other, &obj->blank_flag);
    if (u->length == 0) {
        Py_INCREF(obj);
        return (PyObject *)obj;
    }
    Py_UNICODE* p = P(obj);
    Py_UNICODE* src = u->str;
    Py_ssize_t n = u->length;
    while (n) {
        if (obj->nfree == 0) p = buf_alloc(obj);
        if (*src == '<') {
            *p++ = '&'; if (--obj->nfree == 0) p = buf_alloc(obj);
            *p++ = 'l'; if (--obj->nfree == 0) p = buf_alloc(obj);
            *p++ = 't'; if (--obj->nfree == 0) p = buf_alloc(obj);
            *p++ = ';'; --obj->nfree;
            src++;
        } else if (*src == '&') {
            *p++ = '&'; if (--obj->nfree == 0) p = buf_alloc(obj);
            *p++ = 'a'; if (--obj->nfree == 0) p = buf_alloc(obj);
            *p++ = 'm'; if (--obj->nfree == 0) p = buf_alloc(obj);
            *p++ = 'p'; if (--obj->nfree == 0) p = buf_alloc(obj);
            *p++ = ';'; --obj->nfree;
            src++;
        } else {
            *p++ = *src++; --obj->nfree;
        }
        n--;
    }


    Py_INCREF(obj);
    return (PyObject *)obj;
}

PyObject* buf_str(fastbuf_BufObject* obj)
{
    if (obj->nbuf == 1) {
        Py_ssize_t buflen = BUFLEN - obj->nfree;
        PyObject* u = PyUnicode_FromUnicode(obj->bufs[0], buflen);
        return u;
    }
    PyUnicodeObject* u = (PyUnicodeObject*)PyUnicode_FromUnicode(NULL, obj->nbuf * BUFLEN - obj->nfree);
    if (!u) {
        DEBUGLOG("PyUnicode_FromUnicode no workie %p %ld %ld %ld %ld\n", obj, obj->nbuf, BUFLEN, obj->nfree, obj->nbuf * BUFLEN - obj->nfree);
        return PyErr_NoMemory();
    }
    Py_UNICODE *dst = u->str;
    int i = 0;
    for (; i < obj->nbuf-1; i++) {
        memcpy(dst, obj->bufs[i], BUFSIZE);
        dst += BUFLEN;
    }
    Py_ssize_t len = BUFSIZE - obj->nfree * (sizeof(Py_UNICODE));
    memcpy(dst, obj->bufs[i], len);
    return (PyObject *)u;
}



static
void buf_dealloc(fastbuf_BufObject *buf)
{
    DEBUGLOG("buf_dealloc %p\n", buf);
    while (buf->nbuf) {
        DEBUGLOG("freeing %p\n", buf->bufs[buf->nbuf-1]);
        PyMem_Free(buf->bufs[--buf->nbuf]);
    }
    if (buf->bufs) {
        DEBUGLOG("freeing %p\n", buf->bufs);
        PyMem_Free(buf->bufs);
        buf->bufs = NULL;
    }
    DEBUGLOG("buf_dealloc done\n");
}

PyObject* buf_call(fastbuf_BufObject *buf, PyObject* args, PyObject* kwds) {
    Py_INCREF(buf);
    for (int i = 0; i < PyTuple_Size(args); i++) {
        Py_DECREF(buf_inplace_add(buf, PyTuple_GetItem(args, i)));
    }
    return (PyObject*)buf;
}

PyObject* set_safe_class(PyObject* dummy, PyObject* safe) {
    Py_INCREF(safe);
    safe_class = safe;
    Py_INCREF(Py_None);
    return Py_None;
}

static PyNumberMethods buf_as_number = {
    (binaryfunc)buf_inplace_add,        /*nb_add*/
    (binaryfunc)buf_inplace_and,        /*nb_subtract*/
    0,                                  /*nb_multiply*/
    0,                                  /*nb_divide*/
    0,                                  /*nb_remainder*/
    0,                                  /*nb_divmod*/
    0,                                  /*nb_power*/
    0,                                  /*nb_negative*/
    0,                                  /*nb_positive*/
    0,                                  /*nb_absolute*/
    0,                                  /*nb_bool*/
    0,                                  /*nb_invert*/
    0,                                  /*nb_lshift*/
    0,                                  /*nb_rshift*/
    (binaryfunc)buf_inplace_and,        /*nb_and*/
    0,                                  /*nb_xor*/
    0,                                  /*nb_or*/
    0,                                  /*nb_int*/
    0,                                  /*nb_reserved*/
    0,                                  /*nb_float*/
    0,                                  /*nb_inplace_add*/
    0,                                  /*nb_inplace_subtract*/
    0,                                  /*nb_inplace_multiply*/
    0,                                  /*nb_inplace_remainder*/
    0,                                  /*nb_inplace_power*/
    0,                                  /*nb_inplace_lshift*/
    0,                                  /*nb_inplace_rshift*/
    0,                                  /*nb_inplace_and*/
    0,                                  /*nb_inplace_xor*/
    0,                                  /*nb_inplace_or*/
};

static PyMappingMethods buf_as_mapping = {
    0,                                  /*mp_length*/
    (binaryfunc)buf_inplace_and,        /*mp_subscript*/
    0                                   /*mp_ass_subscript*/
};

static PyTypeObject fastbuf_BufType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "fastbuf.Buf",             /*tp_name*/
    sizeof(fastbuf_BufObject), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)buf_dealloc,   /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    &buf_as_number,            /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    &buf_as_mapping,           /*tp_as_mapping*/
    0,                         /*tp_hash */
    (ternaryfunc)buf_call,     /*tp_call*/
    (reprfunc)buf_str,         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT|Py_TPFLAGS_CHECKTYPES         /*tp_flags*/
};

static PyMethodDef Buf_methods[] = {
    {"__call__", (PyCFunction)buf_inplace_add, METH_O, ""},
    {"append", (PyCFunction)buf_inplace_add, METH_O, ""},
    {"appendq", (PyCFunction)buf_inplace_and, METH_O, ""},
    {NULL}  /* Sentinel */
};

static PyMemberDef Buf_members[] = {
    {"blank_flag", T_INT, offsetof(fastbuf_BufObject, blank_flag), 0,
     "Whether a blank value has been added to this buffer"},
    {NULL}  /* Sentinel */
};
PyObject* buf_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    fastbuf_BufObject* buf = PyObject_New(fastbuf_BufObject, &fastbuf_BufType);
    DEBUGLOG("buf_new %p\n", buf);
    buf->bufs = PyMem_Malloc(NBUF * sizeof(Py_UNICODE*));
    DEBUGLOG("malloc %p\n", buf->bufs);
    buf->bufs[0] = PyMem_Malloc(BUFSIZE);
    DEBUGLOG("malloc %p\n", buf->bufs[0]);
    buf->nbuf = 1;
    buf->nfree = BUFLEN;
    buf->maxbufs = NBUF;
    buf->blank_flag = 0;
    Py_INCREF(buf);
    return (PyObject*)buf;
}

static PyMethodDef fastbufMethods[] = {
    {"set_safe_class",  set_safe_class, METH_O, "Pass in a unicode subclass that won't be quoted"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

PyMODINIT_FUNC
initfastbuf(void)
{
    PyObject *m;

    m = Py_InitModule("fastbuf", fastbufMethods);

    fastbuf_BufType.tp_new = buf_new;
    fastbuf_BufType.tp_methods = Buf_methods;
    fastbuf_BufType.tp_members = Buf_members;
    if (PyType_Ready(&fastbuf_BufType) < 0)
        return;

    Py_INCREF(&fastbuf_BufType);
    PyModule_AddObject(m, "Buf", (PyObject *)&fastbuf_BufType);
}