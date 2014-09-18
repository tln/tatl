#include <Python.h>

// 16k, minus room for malloc overhead
#define BUFSIZE 16300
#define BUFLEN BUFSIZE/sizeof(Py_UNICODE)
#define NBUF 500
typedef struct {
    PyObject_HEAD
    /* Type-specific fields go here. */
    Py_UNICODE **bufs;
    Py_ssize_t nbuf;    /* number of buffers in use */
    Py_ssize_t nfree;   /* number of bytes available in last buffer */
    Py_ssize_t maxbufs; /* size of bufs */
} fastbuf_BufObject;

#define BUF(o) (fastbuf_BufObject*)o
#define P(o) (o->bufs[o->nbuf-1] + (BUFLEN - o->nfree))

Py_UNICODE *buf_alloc(fastbuf_BufObject *buf)
{
    /* Only call when previous buffer is full. */

    /* Grow the bufs array if needed. */
    if (buf->nbuf == buf->maxbufs) {
        buf->maxbufs += NBUF;
        buf->bufs = PyMem_Realloc(buf->bufs, buf->maxbufs * sizeof(Py_UNICODE*));
    }
    buf->nfree = BUFLEN;
    return buf->bufs[buf->nbuf++] = PyMem_Malloc(BUFSIZE);
}

PyObject* buf_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
PyObject* buf_str(fastbuf_BufObject* obj);
PyObject* buf_inplace_add(fastbuf_BufObject* obj, PyObject* other);

PyUnicodeObject *buf_other_to_unicode(PyObject* other)
{
    if (other == Py_None)
        return (PyUnicodeObject *)PyUnicode_FromString("null");
    if (PyList_Check(other) || PyTuple_Check(other)) {
        fastbuf_BufObject* buf = (fastbuf_BufObject*)buf_new(NULL, NULL, NULL);
        PyObject* sp = PyUnicode_FromString(" ");
        for (int i = 0; i < PySequence_Length(other); i++) {
            if (i) buf_inplace_add(buf, sp);
            buf_inplace_add(buf, PySequence_GetItem(other, i));
        }
        return (PyUnicodeObject *)buf_str(buf);
    }
    return (PyUnicodeObject *)PyObject_Unicode(other);
}

PyObject *
buf_inplace_add(fastbuf_BufObject* obj, PyObject* other)
{
    PyUnicodeObject *u = buf_other_to_unicode(other);
    Py_UNICODE *p = P(obj);
    Py_ssize_t n = 0;
    if (obj->nfree == 0) p = buf_alloc(obj);
    while ((u->length - n) > obj->nfree) {
        memcpy(p, u->str + n, obj->nfree * sizeof(Py_UNICODE));
        n += obj->nfree;
        p = buf_alloc(obj);
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
    PyUnicodeObject *u = buf_other_to_unicode(other);
    if (u->length == 0) return (PyObject *)obj;
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

    while (buf->nbuf) PyMem_Free(buf->bufs[--buf->nbuf]);
    PyMem_Free(buf->bufs);
}


PyObject* identity(PyObject* dummy, PyObject* obj) {
    Py_INCREF(obj);
    return obj;
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
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    (reprfunc)buf_str,         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT|Py_TPFLAGS_CHECKTYPES         /*tp_flags*/
};

static PyMethodDef Buf_methods[] = {
    {"append", (PyCFunction)buf_inplace_add, METH_O, ""},
    {"appendq", (PyCFunction)buf_inplace_and, METH_O, ""},
    {NULL}  /* Sentinel */
};

PyObject* buf_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    fastbuf_BufObject* buf = PyObject_New(fastbuf_BufObject, &fastbuf_BufType);
    buf->bufs = PyMem_Malloc(NBUF * sizeof(Py_UNICODE*));
    buf->bufs[0] = PyMem_Malloc(BUFSIZE);
    buf->nbuf = 1;
    buf->nfree = BUFLEN;
    buf->maxbufs = NBUF;
    return (PyObject*)buf;
}

static PyMethodDef fastbufMethods[] = {
    {"identity",  identity, METH_O, "Return argument"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};


PyMODINIT_FUNC
initfastbuf(void)
{
    PyObject *m;

    m = Py_InitModule("fastbuf", fastbufMethods);

    fastbuf_BufType.tp_new = buf_new;
    fastbuf_BufType.tp_methods = Buf_methods;
    if (PyType_Ready(&fastbuf_BufType) < 0)
        return;

    Py_INCREF(&fastbuf_BufType);
    PyModule_AddObject(m, "Buf", (PyObject *)&fastbuf_BufType);
}