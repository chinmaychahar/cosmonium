#
#This file is part of Cosmonium.
#
#Copyright (C) 2018-2019 Laurent Deru.
#
#Cosmonium is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#Cosmonium is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with Cosmonium.  If not, see <https://www.gnu.org/licenses/>.
#

from __future__ import print_function
from __future__ import absolute_import

from ..shaders import DataSource, ShaderAppearance

from .appearances import TextureTilingMode

class TextureDictionaryDataSource(DataSource):
    def __init__(self, dictionary, shader=None):
        DataSource.__init__(self, shader)
        self.dictionary = dictionary
        self.tiling = dictionary.tiling
        self.nb_entries = self.dictionary.nb_blocks
        self.nb_coefs = (self.nb_entries + 3) // 4

    def get_id(self):
        return 'dict' + str(id(self))

    def fragment_uniforms(self, code):
        DataSource.fragment_uniforms(self, code)
        code.append("#define NB_COEFS_VEC %d" % self.nb_coefs)
        if self.dictionary.texture_array:
            for texture in self.dictionary.texture_arrays.values():
                code.append("uniform sampler2DArray %s;" % texture.input_name)
        else:
            for (name, entry) in self.dictionary.blocks.items():
                for texture in entry.textures:
                    code.append("uniform sampler2D tex_%s_%s;" % (name, texture.category))
        code.append("uniform vec2 detail_factor;")

    def hash4(self, code):
        code.append('''
vec4 hash4( vec2 p ) { return fract(sin(vec4( 1.0+dot(p,vec2(37.0,17.0)),
                                              2.0+dot(p,vec2(11.0,47.0)),
                                              3.0+dot(p,vec2(41.0,29.0)),
                                              4.0+dot(p,vec2(23.0,31.0))))*103.0); }
''')

    def textureNoTile(self, code):
        if self.dictionary.texture_array:
            code.append("vec4 textureNoTile(sampler2DArray samp, in vec3 uv)")
        else:
            code.append("vec4 textureNoTile(sampler2D samp, in vec2 uv)")
        code.append(
'''{
    vec2 iuv = floor(uv.xy);
    vec2 fuv = fract(uv.xy);

    // generate per-tile transform
    vec4 ofa = hash4(iuv + vec2(0.0, 0.0));
    vec4 ofb = hash4(iuv + vec2(1.0, 0.0));
    vec4 ofc = hash4(iuv + vec2(0.0, 1.0));
    vec4 ofd = hash4(iuv + vec2(1.0, 1.0));

    vec2 ddx = dFdx(uv.xy);
    vec2 ddy = dFdy(uv.xy);

    // transform per-tile uvs
    ofa.zw = sign(ofa.zw - 0.5);
    ofb.zw = sign(ofb.zw - 0.5);
    ofc.zw = sign(ofc.zw - 0.5);
    ofd.zw = sign(ofd.zw - 0.5);

    // uv's, and derivarives (for correct mipmapping)
    vec2 uva = uv.xy*ofa.zw + ofa.xy; vec2 ddxa = ddx*ofa.zw; vec2 ddya = ddy*ofa.zw;
    vec2 uvb = uv.xy*ofb.zw + ofb.xy; vec2 ddxb = ddx*ofb.zw; vec2 ddyb = ddy*ofb.zw;
    vec2 uvc = uv.xy*ofc.zw + ofc.xy; vec2 ddxc = ddx*ofc.zw; vec2 ddyc = ddy*ofc.zw;
    vec2 uvd = uv.xy*ofd.zw + ofd.xy; vec2 ddxd = ddx*ofd.zw; vec2 ddyd = ddy*ofd.zw;

    // fetch and blend
    vec2 b = smoothstep(0.25, 0.75, fuv);
''')
        if self.dictionary.texture_array:
            code.append('''
    return mix( mix(textureGrad(samp, vec3(uva, uv.z), ddxa, ddya),
                    textureGrad(samp, vec3(uvb, uv.z), ddxb, ddyb), b.x),
                mix(textureGrad(samp, vec3(uvc, uv.z), ddxc, ddyc),
                    textureGrad(samp, vec3(uvd, uv.z), ddxd, ddyd), b.x), b.y);
''')
        else:
            code.append('''
    return mix( mix(textureGrad(samp, uva, ddxa, ddya),
                    textureGrad(samp, uvb, ddxb, ddyb), b.x),
                mix(textureGrad(samp, uvc, ddxc, ddyc),
                    textureGrad(samp, uvd, ddxd, ddyd), b.x), b.y);
''')
        code.append("}")

    def resolve_coefs(self, code, category):
        code.append("vec4 resolve_%s(vec4 coefs[NB_COEFS_VEC], vec2 position) {" % category)
        if self.tiling == TextureTilingMode.F_hash:
            sampler = 'textureNoTile'
        else:
            if self.dictionary.texture_array:
                sampler = 'texture'
            else:
                sampler = 'texture2D'
        code.append("    float coef;")
        code.append("    vec4 result = vec4(0.0);")
        for (block_id, block) in self.dictionary.blocks.items():
            index = self.dictionary.blocks_index[block_id]
            major = index // 4
            minor = index % 4
            tex_id = self.dictionary.get_tex_id_for(block_id, category)
            code.append("    coef = coefs[%d][%d];" % (major, minor))
            code.append("    if (coef > 0) {")
            if self.dictionary.texture_array:
                dict_name = 'array_%s' % category
                #TODO: There should not be a link like that
                if self.shader.appearance.resolved:
                    if category == 'normal':
                        code.append("      vec3 tex_%s = %s(tex_%s, vec3(position.xy * detail_factor, %d)).xyz * 2 - 1;" % (block_id, sampler, dict_name, tex_id))
                    else:
                        code.append("      vec3 tex_%s = %s(tex_%s, vec3(position.xy * detail_factor, %d)).xyz;" % (block_id, sampler, dict_name, tex_id))
                else:
                    if category == 'normal':
                        code.append("      vec3 tex_%s = textureLod(tex_%s, vec3(position.xy * detail_factor, %d), 1000).xyz * 2 - 1;" % (block_id, dict_name, tex_id))
                    else:
                        code.append("      vec3 tex_%s = textureLod(tex_%s, vec3(position.xy * detail_factor, %d), 1000).xyz;" % (block_id, dict_name, tex_id))
            else:
                if category == 'normal':
                    code.append("      vec3 tex_%s = %s(tex_%s_%s, position.xy * detail_factor).xyz * 2 - 1;" % (block_id, sampler, block_id, category))
                else:
                    code.append("      vec3 tex_%s = %s(tex_%s_%s, position.xy * detail_factor).xyz;" % (block_id, sampler, block_id, category))
            code.append("      result.rgb = mix(result.rgb, tex_%s, coef);" % (block_id))
            code.append("    }")
        code.append("    result.w = 1.0;")
        code.append("    return result;")
        code.append("}")

    def fragment_extra(self, code):
        DataSource.fragment_extra(self, code)
        if self.tiling == TextureTilingMode.F_hash:
            self.shader.fragment_shader.add_function(code, 'hash4', self.hash4)
            self.shader.fragment_shader.add_function(code, 'textureNoTile', self.textureNoTile)
        for category in self.dictionary.texture_categories.keys():
            self.resolve_coefs(code, category)

    def get_source_for(self, source, param, error=True):
        for category in self.dictionary.texture_categories.keys():
            if source == 'resolve_tex_dict_' + category:
                return 'resolve_%s(%s)' % (category, ', '.join(param))
        for (name, index) in self.dictionary.blocks_index.items():
            if source == name + '_index':
                return (index, self.nb_coefs)
        if error: print("Unknown source '%s' requested" % source)
        return 0

    def update_shader_shape_static(self, shape, appearance):
        DataSource.update_shader_shape_static(self, shape, appearance)
        shape.instance.set_shader_input("detail_factor", self.dictionary.scale_factor)

class ProceduralMap(ShaderAppearance):
    use_vertex = True
    world_vertex = True
    model_vertex = True

    def __init__(self, textures_control, heightmap, create_normals=False, shader=None):
        ShaderAppearance.__init__(self, shader)
        self.textures_control = textures_control
        self.heightmap = heightmap
        self.has_surface_texture = True
        self.has_normal_texture = create_normals
        self.normal_texture_tangent_space = True
        #self.textures_control.set_heightmap(self.heightmap)
        self.has_attribute_color = False
        self.has_vertex_color = False
        self.has_material = False

    def get_id(self):
        config = "pm"
        if self.has_normal_texture:
            config += '-n'
        return config

    def fragment_shader(self, code):
        code.append('vec3 surface_normal = %s;' % self.shader.data_source.get_source_for('normal_%s' % self.heightmap.name, 'texcoord0.xy'))
        code.append("float height = %s;" % self.shader.data_source.get_source_for('height_%s' % self.heightmap.name, 'texcoord0.xy'))
        code.append('vec2 uv = texcoord0.xy;')
        code.append('float angle = surface_normal.z;')
        if True:
            #self.textures_control.color_func_call(code)
            #code.append("surface_color = vec4(%s_color, 1.0);" % self.textures_control.name)
            code.append("surface_color = vec4(height, height, height, 1.0);")
        else:
            code += ['surface_color = vec4(surface_normal, 1.0);']
        if self.has_normal_texture:
            code += ['pixel_normal = surface_normal;']

class DetailMap(ShaderAppearance):
    use_vertex = True
    world_vertex = True
    model_vertex = True

    def __init__(self, textures_control, heightmap, create_normals=True, shader=None):
        ShaderAppearance.__init__(self, shader)
        self.textures_control = textures_control
        self.heightmap = heightmap
        self.textures_control.set_heightmap(self.heightmap)
        self.create_normals = create_normals
        self.normal_texture_tangent_space = True
        self.resolved = False

    def create_shader_configuration(self, appearance):
        self.textures_control.create_shader_configuration(appearance)
        self.has_surface = True
        self.has_normal = self.create_normals or self.textures_control.has_normal
        self.has_occlusion = self.textures_control.has_occlusion

    def get_id(self):
        name = "dm"
        config = ""
        if self.has_surface:
            config += "u"
        if self.has_occlusion:
            config += "o"
        if self.has_normal:
            config += "n"
        if self.resolved:
            config += 'r'
        if config != "":
            return name + '-' + config
        else:
            return name

    def set_shader(self, shader):
        ShaderAppearance.set_shader(self, shader)
        self.textures_control.set_shader(shader)

    def set_resolved(self, resolved):
        self.resolved = resolved

    def vertex_uniforms(self, code):
        code.append("uniform vec4 flat_coord;")

    def vertex_outputs(self, code):
        code.append("out vec2 flat_position;")

    def vertex_shader(self, code):
        code.append("flat_position.x = flat_coord.x + flat_coord.z * texcoord0.x;")
        code.append("flat_position.y = flat_coord.y + flat_coord.w * (1.0 - texcoord0.y);")

    def fragment_uniforms(self, code):
        ShaderAppearance.fragment_uniforms(self, code)
        self.textures_control.fragment_uniforms(code)

    def fragment_inputs(self, code):
        code.append("in vec2 flat_position;")

    def fragment_extra(self, code):
        self.textures_control.fragment_extra(code)

    def fragment_shader_decl(self, code):
        ShaderAppearance.fragment_shader_decl(self, code)
        code.append('vec2 position = flat_position;')

    def fragment_shader(self, code):
        code.append('vec3 surface_normal = %s;' % self.shader.data_source.get_source_for('normal_%s' % self.heightmap.name, 'texcoord0.xy'))
        code.append("float height = %s;" % self.shader.data_source.get_source_for('height_%s' % self.heightmap.name, 'texcoord0.xy'))
        code.append('vec2 uv = texcoord0.xy;')
        code.append('float angle = surface_normal.z;')
        self.textures_control.color_func_call(code)
        if self.textures_control.has_albedo:
            self.textures_control.get_value(code, 'albedo')
            code.append("surface_color = %s_albedo;" % self.textures_control.name)
        if self.has_normal:
            if self.textures_control.has_normal:
                self.textures_control.get_value(code, 'normal')
                code.append("vec3 n1 = surface_normal + vec3(0, 0, 1);")
                code.append("vec3 n2 = %s_normal.xyz * vec3(-1, -1, 1);" % self.textures_control.name)
                code.append("pixel_normal = n1 * dot(n1, n2) / n1.z - n2;")
            else:
                code.append("pixel_normal = surface_normal;")
        if self.textures_control.has_occlusion:
            self.textures_control.get_value(code, 'occlusion')
            code.append("surface_occlusion = %s_occlusion.x;" % self.textures_control.name)

    def update_shader_shape_static(self, shape, appearance):
        ShaderAppearance.update_shader_shape_static(self, shape, appearance)
        self.textures_control.update_shader_shape_static(shape, appearance)

    def update_shader_patch_static(self, shape, patch, appearance):
        ShaderAppearance.update_shader_patch_static(self, shape, patch, appearance)
        self.textures_control.update_shader_patch_static(shape, patch, appearance)
        patch.instance.set_shader_input("flat_coord", patch.flat_coord)
