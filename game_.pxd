cdef class LevelData:
    cdef public int number, checkpoint
    cdef public str root, bgpath
    cdef public bool success
    cdef public dict meta
    cdef public tuple size
    cdef public list tiles

    def __init__(self, number)
    cdef _get_file_path(self, file)
    cdef _init_attrs(self)
    cdef _load_level(self)
