# https://en.wikipedia.org/wiki/Linear_congruential_generator
class LCG(object):
    def __init__(self, seed=1):
        self.state = seed

    def _random(self):
        self.state = (self.state * 1103515245 + 12345) & 0x7FFFFFFF
        return self.state

    def random(self):
        return self._random() / 2147483647.  # 0x7FFFFFFF in decimal

    def randint(self, a, b):
        rng = self._random() % (b - a + 1)
        return rng + a

    def choice(self, seq):
        return seq[int(self.random() * len(seq))]  # raises IndexError if seq is empty

    def shuffle(self, seq):
        for i in reversed(range(1, len(seq))):
            # pick an element in x[:i+1] with which to exchange x[i]
            j = int(self.random() * (i+1))
            seq[i], seq[j] = seq[j], seq[i]

    def serialize(self):
        return self.state

    def deserialize(self, seed):
        self.state = seed

class StaticRandom(object):
    def __init__(self, seed=0):
        self.set_seed(seed)

    def set_seed(self, seed):
        self.seed = seed
        self.combat_random = LCG(seed)
        self.growth_random = LCG(seed + 1)
        self.other_random = LCG(seed + 2)
        
r = StaticRandom()

def set_seed(seed):
    r.set_seed(seed)

def get_combat():
    return r.combat_random.randint(0, 99)

def get_growth():
    return r.growth_random.randint(0, 99)

def get_levelup(u_id, lvl):
    return LCG(hash(u_id) + lvl + r.seed)

def get_combat_random_state():
    return r.combat_random.state

def set_combat_random_state(state):
    r.combat_random.state = state

def shuffle(lst):
    r.other_random.shuffle(lst)
    return lst

# def get_other(a, b):
#     return r.other_random.randint(a, b)

# def get_other_random_state():
#     return r.other_random.state

# def set_other_random_state(state):
#     r.other_random.state = state

if __name__ == '__main__':
    print(get_combat())
    state = r.combat_random.serialize()
    print(get_combat())
    print(get_combat())
    r.combat_random.deserialize(state)
    print(get_combat())
    print(get_combat())
    L = [1, 2, 3, 4, 5, 6, 7]
    print(L)
    shuffle(L)
    print(L)