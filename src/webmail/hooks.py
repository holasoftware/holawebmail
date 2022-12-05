import collections

_hooks = collections.defaultdict(lambda: list())


def append_hook(event, cb):
    _hooks[event].append(cb)

# trigger_hook
def dispatch_hook(key, hook_data, **kwargs):
    """Dispatches a hook dictionary on a given piece of data."""
    hooks = _hooks.get(key, None)
    if hooks:
        for hook in hooks:
            _hook_data = hook(hook_data, **kwargs)
            if _hook_data is not None:
                hook_data = _hook_data
    return hook_data
