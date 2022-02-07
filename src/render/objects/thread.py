from ..component import LifecycleComponent


class ThreadComponent(LifecycleComponent):
    def __init__(self, scene, func):
        self.lifecycle = func
        super().__init__(scene)

    lifecycle = None  # modified on __init__
