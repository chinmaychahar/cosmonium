from __future__ import print_function

#TODO: Merge with ShapeObject ?
class TerrainObject(object):
    def __init__(self, shape=None, appearance=None, shader=None):
        self.parent = None
        self.owner = None
        self.shape = None
        self.set_shape(shape)
        self.appearance = appearance
        self.shader = shader
        self.instance = None
        self.instance_ready = False

    def set_shape(self, shape):
        if self.shape is not None:
            self.shape.set_owner(None)
            self.shape.parent = None
            self.shape = None
        self.shape = shape
        if shape is not None:
            self.shape.set_owner(self.owner)
            self.shape.parent = self

    def set_parent(self, parent):
        self.parent = parent

    def set_owner(self, owner):
        self.owner = owner
        if self.shape is not None:
            self.shape.set_owner(owner)

    def set_appearance(self, appearance):
        self.appearance = appearance

    def set_shader(self, shader):
        self.shader = shader

    def add_after_effect(self, after_effect):
        if self.shader is not None:
            self.shader.add_after_effect(after_effect)

    def apply_instance(self, instance):
        if instance != self.instance:
            self.instance = instance
        if self.appearance is not None:
            self.appearance.bake()
            self.appearance.apply(self.shape, self.shader)
        if self.shader is not None:
            self.shader.apply(self.shape, self.appearance)
            self.shader.update(self.shape, self.appearance)
        self.shape.apply_owner()
        self.instance.reparentTo(render)
        self.instance_ready = True

    def create_instance(self, callback=None, cb_args=()):
        #print("Loading", self.parent.get_name())
        self.instance = self.shape.create_instance(callback, cb_args)
        if not self.shape.deferred_instance:
            self.apply_instance(self.instance)
        else:
            self.shape.apply_owner()
        return self.instance

    def remove_instance(self):
        if self.instance:
            self.instance.removeNode()
            self.instance = None
            self.instance_ready = False

    def update_shader(self):
        if self.instance is not None and self.shader is not None:
            self.shader.apply(self.shape, self.appearance)

    def update_instance(self):
        if self.shader is not None:
            self.shader.update(self.shape, self.appearance)
