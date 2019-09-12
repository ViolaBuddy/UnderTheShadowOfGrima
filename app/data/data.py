class data(object):
    """
    Only accepts data points that have nid attribute
    """

    def __init__(self, vals=None):
        if vals:
            self._list = vals
            self._dict = {val.nid: val for val in vals}
        else:
            self._list = []
            self._dict = {}

    def values(self):
        return self._list

    def keys(self):
        return [val.nid for val in self._list]

    def items(self):
        return [(val.nid, val) for val in self._list]

    def get(self, key, fallback=None):
        return self._dict.get(key, fallback)

    def append(self, val):
        self._list.append(val)
        self._dict[val.nid] = val

    def delete(self, val):
        # Fails silently
        if val.nid in self._dict:
            self._list.remove(val)
            del self._dict[val.nid]

    def pop(self, idx=None):
        if idx is None:
            idx = len(self._list) - 1
        r = self._list.pop(idx)
        del self._dict[r.nid]

    def insert(self, idx, val):
        self._list.insert(idx, val)
        self._dict[val.nid] = val

    def clear(self):
        self._list = []
        self._dict = {}

    def index(self, nid):
        for idx, val in enumerate(self._list):
            if val.nid == nid:
                return idx
        raise ValueError

    # Saving functions
    def serialize(self):
        return self._list

    @classmethod
    def deserialize(cls, vals):
        return cls(vals)

    def restore(self, vals):
        self.clear()
        for val in vals:
            self.append(val)

    # Magic Methods
    def __repr__(self):
        return self._list

    def __len__(self):
        return len(self._list)

    def __getitem__(self, key):
        return self._dict[key]

    def __iter__(self):
        return iter(self._list)