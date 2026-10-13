"""registry.py - scene registry shared by the scene modules and the renderer."""
SCENES = []          # (name, duration, fn)
EVENTS = {}          # name -> list of (t, sfx, gain)


def scene(name, dur, events=()):
    def deco(fn):
        SCENES.append((name, dur, fn))
        EVENTS[name] = list(events)
        return fn
    return deco
