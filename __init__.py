found_blender = False
try:
    import bpy,math
except:
    pass

bl_info = {
    "name": "Bake Groups",
    "description": "Helper Tool to bake materials to textures. Define groups of objects, create automatically atlas, bake",
    "author": "Thomas Trocha",
    "version": (0, 0, 2),
    "blender": (2, 80, 0),
    "location": "View3D",
    "warning": "This addon is still in development.",
    "wiki_url": "",
    "category": "Object" }


bakesetting_normal_axis = [ (axis[0],axis[1],axis[1]) for axis in [["POS_X","+X"],["POS_Y","+Y"],["POS_Z","+Z"],
                                                          ["NEG_X","-X"],["NEG_Y","-Y"],["NEG_Z","-Z"]] ]

bake_types = [(bt,bt,bt) for bt in ['DIFFUSE', 'ROUGHNESS', 'AO', 'SHADOW', 'NORMAL', 'UV', 'EMIT', 'ENVIRONMENT', 'COMBINED', 'GLOSSY', 'TRANSMISSION', 'SUBSURFACE']]
bake_types_with_customsettings = ['DIFFUSE', 'NORMAL', 'COMBINED', 'GLOSSY', 'TRANSMISSION', 'SUBSURFACE']


def GetAtlasGroupByName(name):
    settings = bpy.context.scene.world.atlasSettings

    idx = 0
    for atlas_group in settings.atlas_groups:
        if atlas_group.name == name:
            return atlas_group,idx
        idx = idx + 1
    return None,-1

# get material_indices actually used by the mesh
def used_material_indices(mesh):
    used_mat_indices = []
    for face in mesh.polygons:
        if face.material_index not in used_mat_indices:
            used_mat_indices.append(face.material_index)
    return used_mat_indices

# ensure that you can only select mesh-objects
def mesh_object_poll(self,object):
    if object.type!="MESH":
        return False

    # todo prevent selection of one object multiple times        
    return True
    
# output all object-uvmaps    
def AtlasGroupItemUVCallback(self, context):
    groups = []

    idx=0
    for uv in self.obj.data.uv_layers:
        groups.append((str(idx),uv.name,uv.name,idx))
        idx = idx + 1

    return groups

# create backup of current bakesettings
def push_current_bakesettings():
    print("backup bakesettings")
    current = bpy.context.scene.render.bake
    backup = bpy.context.scene.world.atlasSettings.before_bakesettings

    backup.use_pass_direct = current.use_pass_direct
    backup.use_pass_indirect = current.use_pass_indirect
    backup.use_pass_color = current.use_pass_color
    # combined
    backup.use_pass_diffuse = current.use_pass_diffuse
    backup.use_pass_glossy = current.use_pass_glossy
    backup.use_pass_transmission = current.use_pass_transmission
    backup.use_pass_subsurface = current.use_pass_subsurface
    backup.use_pass_ambient_occlusion = current.use_pass_ambient_occlusion
    backup.use_pass_emit = current.use_pass_emit
    # normal
    backup.normal_space = current.normal_space
    backup.normal_r = current.normal_r
    backup.normal_g = current.normal_g
    backup.normal_b = current.normal_b

# set bakesettings
def set_bakesettings(settings):
    print("set bake-settings")
    current = bpy.context.scene.render.bake

    current.use_pass_direct = settings.use_pass_direct
    current.use_pass_indirect = settings.use_pass_indirect
    current.use_pass_color = settings.use_pass_color
    # combined
    current.use_pass_diffuse = settings.use_pass_diffuse
    current.use_pass_glossy = settings.use_pass_glossy
    current.use_pass_transmission = settings.use_pass_transmission
    current.use_pass_subsurface = settings.use_pass_subsurface
    current.use_pass_ambient_occlusion = settings.use_pass_ambient_occlusion
    current.use_pass_emit = settings.use_pass_emit
    # normal
    current.normal_space = settings.normal_space
    current.normal_r = settings.normal_r
    current.normal_g = settings.normal_g
    current.normal_b = settings.normal_b

#########################
# Settings PropertyGroups    
#########################
class RearrangeSettings(bpy.types.PropertyGroup):
    uv_name             : bpy.props.StringProperty(default="Generated")
    uv_name_overwrite   : bpy.props.BoolProperty(default=True)
    uv_autoset_bakeuv   : bpy.props.BoolProperty(default=True,description="automatically set the generated uv as bake-uv for all object's bake-group")
    uv_split_multimaterial : bpy.props.BoolProperty(default=False, description="give every material a slot/slotpart of its own(e.g. if uvmaps are colliding)")
    uv_pack_multimaterial: bpy.props.BoolProperty(default=False,description="pack multiple mesh-materials on one uv-slot (squash on x-axis) or give each material one uv-slot(default)")

class AtlasGroupBakeItemSettings(bpy.types.PropertyGroup):
    show_settings: bpy.props.BoolProperty(default=False,description="show settings")
    bake_type: bpy.props.StringProperty()
    
    use_pass_direct: bpy.props.BoolProperty()
    use_pass_indirect: bpy.props.BoolProperty()
    use_pass_color: bpy.props.BoolProperty(default=True)
    # combined
    use_pass_diffuse: bpy.props.BoolProperty()
    use_pass_glossy: bpy.props.BoolProperty()
    use_pass_transmission: bpy.props.BoolProperty()
    use_pass_subsurface: bpy.props.BoolProperty()
    use_pass_ambient_occlusion: bpy.props.BoolProperty()
    use_pass_emit: bpy.props.BoolProperty()
    # normal
    normal_space: bpy.props.EnumProperty(items=[("TANGENT","TANGENT","TANGENT"),("OBJECT","OBJECT","OBJECT")])
    normal_r: bpy.props.EnumProperty(items=bakesetting_normal_axis,default="POS_X")
    normal_g:bpy.props.EnumProperty(items=bakesetting_normal_axis,default="POS_Y")
    normal_b:bpy.props.EnumProperty(items=bakesetting_normal_axis,default="POS_Z")



class AtlasGroupItem(bpy.types.PropertyGroup):
    obj : bpy.props.PointerProperty(type=bpy.types.Object,poll=mesh_object_poll)
    atlas_uv : bpy.props.EnumProperty(items=AtlasGroupItemUVCallback, description="UVMap used for baking")

class AtlasGroupBakeItem(bpy.types.PropertyGroup):
    active : bpy.props.BoolProperty(default=True)
    bake_type : bpy.props.EnumProperty(items=bake_types)
    image : bpy.props.PointerProperty(type=bpy.types.Image)
    bake_settings : bpy.props.PointerProperty(type=AtlasGroupBakeItemSettings)

class AtlasGroup(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty(default="noname")
    show_details : bpy.props.BoolProperty(default=True)
    atlas_items : bpy.props.CollectionProperty(type=AtlasGroupItem)
    bake_items: bpy.props.CollectionProperty(type=AtlasGroupBakeItem)
    selection_idx : bpy.props.IntProperty()
    bake_selection_idx : bpy.props.IntProperty()
    uv_rearrange_settings : bpy.props.PointerProperty(type=RearrangeSettings)


class AtlasData(bpy.types.PropertyGroup):
    saveimage_after_bake : bpy.props.BoolProperty(default=True,description="save image after bake if filepath is set")
    atlas_groups : bpy.props.CollectionProperty(type=AtlasGroup)
    selection_idx : bpy.props.IntProperty()
    before_bakesettings : bpy.props.PointerProperty(type=AtlasGroupBakeItemSettings)
    negative_bool : bpy.props.BoolProperty(name="",description="") # super silly
    ## uv (re)arrange ui-data
    uv_rearrange_atlasname : bpy.props.StringProperty()


##############################################
##              Atlas-Group
##############################################

###################
# atlas group items (object/uv)
###################
class SIMPLEATLAS_UL_LIST_ATLASGROUP_ITEM(bpy.types.UIList):
    """Atlasgroup UIList."""

    def draw_item(self, context, layout, data, item, icon, active_data,active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            row.prop(item,"obj")
            if item.obj:
                row = layout.row()
                if len(item.obj.data.uv_layers)==0:
                    row.label(text="no uvmaps",icon="ERROR")
                else:
                    if item.atlas_uv:
                        row.prop(item,"atlas_uv",text="bake uv")
                    else:
                        row.prop(item,"atlas_uv",text="bake uv",icon="ERROR")
                
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=item.obj.name)

class UL_SIMPLEATLAS_LIST_ATLASGROUPITEM_CREATE(bpy.types.Operator):
    """Add a new item to the list."""

    bl_idname = "simpleatlas.create_group_item"
    bl_label = "Add a new atlas group"

    atlas_group_idx : bpy.props.IntProperty()

    def execute(self, context):
        context.scene.world.atlasSettings.atlas_groups[self.atlas_group_idx].atlas_items.add()
        return{'FINISHED'}

class UL_SIMPLEATLAS_LIST_ATLASGROUPITEM_DELETE(bpy.types.Operator):
    """Add a new item to the list."""

    bl_idname = "simpleatlas.delete_group_item"
    bl_label = "Add a new atlas group"

    atlas_group_idx : bpy.props.IntProperty()

    def execute(self, context):
        group = context.scene.world.atlasSettings.atlas_groups[self.atlas_group_idx]
        index = group.selection_idx
        group.atlas_items.remove(index)
        group.selection_idx = min(max(0, index - 1), len(group.atlas_items) - 1)
        return{'FINISHED'}

class UL_SIMPLEATLAS_LIST_ATLASGROUPITEM_SELECT(bpy.types.Operator):
    """Add a new item to the list."""

    bl_idname = "simpleatlas.select_group_item"
    bl_label = "Add a new atlas group"

    atlas_group_idx : bpy.props.IntProperty()

    def execute(self, context):
        group = context.scene.world.atlasSettings.atlas_groups[self.atlas_group_idx]
        index = group.selection_idx
        item = group.atlas_items[index]

        # force object mode
        item.obj.select_set(state=True)
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()

        return{'FINISHED'}        

############################################
# atlas group bake items (bake type, bake to image)
###########################################
class UL_SIMPLEATLAS_LIST_ATLASGROUPBAKEITEM_CREATE(bpy.types.Operator):
    """Add a new item to the list."""

    bl_idname = "simpleatlas.create_bake_item"
    bl_label = "Add a new atlas group"

    atlas_group_idx : bpy.props.IntProperty()

    def execute(self, context):
        context.scene.world.atlasSettings.atlas_groups[self.atlas_group_idx].bake_items.add()
        return{'FINISHED'}

class UL_SIMPLEATLAS_LIST_ATLASGROUPBAKEITEM_DELETE(bpy.types.Operator):
    """Add a new item to the list."""

    bl_idname = "simpleatlas.delete_bake_item"
    bl_label = "Add a new atlas group"

    atlas_group_idx : bpy.props.IntProperty()
    index : bpy.props.IntProperty()

    def execute(self, context):
        group = context.scene.world.atlasSettings.atlas_groups[self.atlas_group_idx]
        group.bake_items.remove(self.index)
        return{'FINISHED'}


########
# groups
########
class UL_SIMPLEATLAS_LIST_ATLASGROUPS_CREATE(bpy.types.Operator):
    """Add a new item to the list."""

    bl_idname = "simpleatlas.create_group"
    bl_label = "Add a new atlas group"

    def execute(self, context):
        newgrp = context.scene.world.atlasSettings.atlas_groups.add()
        # add a fist atlas-item on group-creation
        newgrp.bake_items.add()
        return{'FINISHED'}

class UL_SIMPLEATLAS_LIST_ATLASGROUPS_DELETE(bpy.types.Operator):
    """Delete the selected item from the list."""

    bl_idname = "simpleatlas.delete_group"
    bl_label = "Deletes an atlasgroup"

    index : bpy.props.IntProperty()    

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        atlasGroupList = context.scene.world.atlasSettings.atlas_groups

        atlasGroupList.remove(self.index)
        return{'FINISHED'}


class UL_SIMPLEATLAS_LIST_ATLASGROUPS_MOVE(bpy.types.Operator):
    """Move an item in the list."""

    bl_idname = "simpleatlas.move_group"
    bl_label = "Move an atlas group in the list"

    direction : bpy.props.EnumProperty(items=(('UP', 'Up', ""),
                                              ('DOWN', 'Down', ""),))
    index : bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        atlasGroupList = context.scene.world.atlasSettings.atlas_groups

        neighbor = self.index + (-1 if self.direction == 'UP' else 1)
        atlasGroupList.move(neighbor, self.index)

        return{'FINISHED'}


## TODO: make the 'bake-all'-operator modal, wait for the bake-process to be finished and then clean up
class BakeAll(bpy.types.Operator):
    """Bakes atlas-groups"""

    bl_idname = "simpleatlas.bake"
    bl_label = "Bake atlas"

    # -1 = all
    atlasid : bpy.props.IntProperty(default=-1)
    only_select : bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        return True

    def bake(self,context,atlasgroup):
        atlas_settings = context.scene.world.atlasSettings

        if len(atlasgroup.bake_items)==0:
            print("atlas group:%s NO bake-elements")
            return

        # keep track of materials in which we set an image-texture
        handled_materials = []

        created_nodes = []
        
        # force object mode
        bpy.ops.object.mode_set(mode="OBJECT",toggle=False)        
        # deselect all objects
        bpy.ops.object.select_all(action='DESELECT')

        for item in atlasgroup.atlas_items:
            if not item.obj:
                continue

            if not item.atlas_uv or len(item.obj.data.uv_layers)==0:
                print("Object %s has not uvlayers set" % item.obj.name)
                continue

            # select the object
            item.obj.select_set(state=True)

            # set active uvmaps to the atlas ones
            item.obj.data.uv_layers.active_index = int(item.atlas_uv)

            for mat_slot in item.obj.material_slots:
                if mat_slot.material in handled_materials or self.only_select:
                    continue

                mat = mat_slot.material

                handled_materials.append(mat)
                nodes = mat.node_tree.nodes

                for node in nodes:
                    node.select=False

                imageTexNode = nodes.new("ShaderNodeTexImage")
                imageTexNode.select=True
                
                nodes.active=imageTexNode
                created_nodes.append(imageTexNode)

        if self.only_select:
            # we only want to select all objects and its bake-uvs
            return


        # iterate over all bake-items and bake them
        for bake_item in atlasgroup.bake_items:
            if not bake_item.image:
                print("no image for bake_type:%s" % bake_item.bake_type)
                continue

            if not bake_item.active:
                print("ignore deactivted bake-pass:%s" % bake_item.bake_type)
                continue

            # set the texture to all temp-imageTexNodes
            for imgTexNode in created_nodes:
                imgTexNode.image = bake_item.image
            
            set_bakesettings(bake_item.bake_settings)

            # bake
            print("bake %s" % bake_item.bake_type)
            bpy.ops.object.bake(type=bake_item.bake_type)
            if atlas_settings.saveimage_after_bake and bake_item.image.filepath:
                bake_item.image.save()


        # cleanup
        
        # remove nodes from its nodetree
        for node in created_nodes:
            node.id_data.nodes.remove(node)

        handled_materials.clear()
        created_nodes.clear()



    def execute(self, context):
        # create backup of current bakesettings
        push_current_bakesettings()

        atlas_settings = context.scene.world.atlasSettings
        atlas_group_list = atlas_settings.atlas_groups

        if self.atlasid==-1:
            for atlas_group in atlas_group_list:
                self.bake(context,atlas_group)
        else:
            bakeGrp = atlas_group_list[self.atlasid]
            self.bake(context,bakeGrp)

        set_bakesettings(atlas_settings.before_bakesettings)

        return{'FINISHED'}


class SimpleAtlasRenderUI(bpy.types.Panel):
    bl_idname = "RENDER_PT_simple_atlas"
    bl_label = "Bake Groups"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    #bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        return bpy.context.scene.render.engine=="CYCLES"

    # Draw the export panel
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.world.atlasSettings

        idx = 0
        for atlas_group in settings.atlas_groups:
            box = layout.box()
            
            if atlas_group.show_details:
                row = box.row()
                row.label(text=("Bake Group: %s" % atlas_group.name ) ) 
                row = box.row()
                row.prop(atlas_group,"name")
            else:
                row = box.row()
                row.label(text=atlas_group.name)

            row.prop(atlas_group,"show_details",text="details")

            bakeop = row.operator('simpleatlas.bake',text="select")
            bakeop.atlasid=idx
            bakeop.only_select=True

            bakeop = row.operator('simpleatlas.bake',text="bake")
            bakeop.atlasid=idx
            bakeop.only_select=False

            op = row.operator('simpleatlas.move_group',text="",icon="TRIA_UP")
            op.direction='UP'
            op.index=idx
            op = row.operator('simpleatlas.move_group',text="",icon="TRIA_DOWN")
            op.direction='DOWN'
            op.index=idx

            if atlas_group.show_details:
                op = row.operator('simpleatlas.delete_group', text='',icon="X")
                op.index=idx


            if atlas_group.show_details:
                row = box.row()
                row.template_list("SIMPLEATLAS_UL_LIST_ATLASGROUP_ITEM","The_list",atlas_group,"atlas_items",atlas_group,"selection_idx")
                row = box.row()
                row.operator('simpleatlas.create_group_item', text='add obj').atlas_group_idx=idx
                row.operator('simpleatlas.delete_group_item', text='del obj').atlas_group_idx=idx
                row.operator('simpleatlas.select_group_item', text='select obj').atlas_group_idx=idx
                row.operator('image.new', text="", icon="FILE_IMAGE")
 
                box.separator()

                #row = layout.row()
                bake_item_idx=0
                for bake_item in atlas_group.bake_items:
                    row = box.row()
                    row.prop(bake_item,"active",text="")
                    col = row.column()
                    col.enabled=bake_item.active
                    col.prop(bake_item,"bake_type",text="bake type")
                    col = row.column()
                    col.enabled=bake_item.active
                    if bake_item.image:
                        col.prop(bake_item,"image")
                    else:
                        col.prop(bake_item,"image",icon="ERROR")

                    bsettings = bake_item.bake_settings

                    has_settings = bake_item.bake_type in bake_types_with_customsettings
                    col = row.column()
                    if has_settings:
                        col.prop(bsettings,"show_settings",text="",icon="OPTIONS",toggle=True)
                        col.enabled=True
                    else:
                        col.prop(settings,"negative_bool",text="",toggle=True)
                        col.enabled=False
                    col.enabled=bake_item.active


                    if bsettings.show_settings:
                        col = box.column()
                        col.enabled=bake_item.active

                        if bake_item.bake_type in {'DIFFUSE', 'GLOSSY', 'TRANSMISSION', 'SUBSURFACE'}:
                            row = col.row(align=True)
                            row.use_property_split = False
                            row.prop(bsettings, "use_pass_direct", toggle=True,text="Direct")
                            row.prop(bsettings, "use_pass_indirect", toggle=True,text="Indirect")
                            row.prop(bsettings, "use_pass_color", toggle=True,text="Color")


                        elif bake_item.bake_type == 'NORMAL':
                            col.prop(bsettings, "normal_space", text="Space")

                            sub = col.column(align=True)
                            sub.prop(bsettings, "normal_r", text="Swizzle R")
                            sub.prop(bsettings, "normal_g", text="G")
                            sub.prop(bsettings, "normal_b", text="B")

                        elif bake_item.bake_type == 'COMBINED':
                            row = col.row(align=True)
                            row.use_property_split = False
                            row.prop(bsettings, "use_pass_direct", toggle=True,text="Direct")
                            row.prop(bsettings, "use_pass_indirect", toggle=True,text="Indirect")

                            flow = col.grid_flow(row_major=False, columns=0, even_columns=False, even_rows=False, align=True)

                            flow.active = bsettings.use_pass_direct or bsettings.use_pass_indirect
                            flow.prop(bsettings, "use_pass_diffuse",text="Diffuse")
                            flow.prop(bsettings, "use_pass_glossy",text="Glossy")
                            flow.prop(bsettings, "use_pass_transmission",text="Transmission")
                            flow.prop(bsettings, "use_pass_subsurface",text="Subsurface")
                            flow.prop(bsettings, "use_pass_ambient_occlusion",text="Ambient Occlusion")
                            flow.prop(bsettings, "use_pass_emit",text="Emit")

                    op = row.operator('simpleatlas.delete_bake_item', text="", icon="X")
                    op.atlas_group_idx=idx
                    op.index=bake_item_idx


                    bake_item_idx = bake_item_idx + 1

                row = box.row()
                row.operator('simpleatlas.create_bake_item', text='add bake-type').atlas_group_idx=idx


            idx = idx + 1
            if atlas_group.show_details:
                layout.separator()

        layout.prop( bpy.context.scene.render.bake,"use_clear",text="clear images before bake")
        layout.prop(settings,"saveimage_after_bake",text="save images after bake")

        box = layout.box()
        row = box.row()

        row.operator('simpleatlas.create_group', text='new bake group',icon="MONKEY")

        row = box.row()
        bakeop = row.operator('simpleatlas.bake',text="bake all groups",icon="IMAGE")
        bakeop.atlasid=-1
        bakeop.only_select=False

def get_uv_index(mesh,uv):
    idx = 0
    for _uv in mesh.uv_layers:
        if _uv == uv:
            return idx
        idx = idx + 1
    return None

###################################################
# (Re)arrange uvs
###################################################
class Rearrange(bpy.types.Operator):
    """automatically arrange uvs"""

    bl_idname = "simpleatlas.uv_arrange"
    bl_label = "Create UVMap"


    def execute(self, context):
        settings = bpy.context.scene.world.atlasSettings
        
        atlas_grp,atlas_grp_idx = GetAtlasGroupByName(settings.uv_rearrange_atlasname)

        if not atlas_grp:
            return{'FINISHED'}


        rsettings = atlas_grp.uv_rearrange_settings
        pack_multi_material = rsettings.uv_pack_multimaterial

        # amout of uv-slots to be used for the newly atlas
        slot_amount = 0
        tex_amount = 0

        material_idx_map={} # key: mesh value: list of used material indices

        # retrieve valid items
        valid_items = []
        for item in atlas_grp.atlas_items:
            if item.obj and item.obj.data not in material_idx_map:
                valid_items.append(item)
                used_materials = used_material_indices(item.obj.data)
                material_idx_map[item.obj.data]=used_materials

                tex_amount = tex_amount + len(used_materials)
                if pack_multi_material or not rsettings.uv_split_multimaterial:
                    slot_amount = slot_amount + 1
                else:
                    slot_amount = slot_amount + len(used_materials)

        
        if slot_amount == 0:
            return{'FINISHED'}

        if len(valid_items) == 1:
            slot_amount = 1

        elems_per_col = math.ceil(math.sqrt(slot_amount))
        dt = 1.0 / elems_per_col # and row
        
        # scale a bit down to have some space between single uvs
        scale = dt * 0.95

        pos_x = 0.0
        pos_y = 0.0


        print("DT:%s" % dt)

        # set pivot-mode 'cursor'
        bpy.ops.object.mode_set(mode="EDIT",toggle=False)
        bpy.context.space_data.pivot_point = 'CURSOR'
        # set the uv-cursor
        bpy.ops.uv.cursor_set(location=(0,0))
        

        for item in valid_items:
            bpy.ops.object.mode_set(mode="OBJECT",toggle=False)
            print("PROCESS:%s" %item.obj.name)
            # deselect all objects
            bpy.ops.object.select_all(action='DESELECT')

            # select obj
            bpy.context.view_layer.objects.active = item.obj   # Make the current obj the active object 
            item.obj.select_set(state=True)

            if (rsettings.uv_name_overwrite):
                # check if we already got an uvmap with that name => remove it
                for uvmap in item.obj.data.uv_layers:
                    if uvmap.name == rsettings.uv_name:
                        item.obj.data.uv_layers.remove(uvmap)

            # get render UV
            renderUV = GetRenderUV(item.obj.data)
            # select render UV
            item.obj.data.uv_layers.active = renderUV
            # copy render UV
            newuv = item.obj.data.uv_layers.new()
            # select new UV to make it the one we manipulate
            item.obj.data.uv_layers.active = newuv

            if rsettings.uv_autoset_bakeuv:
                uv_idx = get_uv_index(item.obj.data,newuv)
                print ("autoset bakeuv:%s" % uv_idx)
                if uv_idx:
                    item.atlas_uv = str(uv_idx)
            print("1")
            newuv.name=rsettings.uv_name

            #bpy.ops.mesh.select_all(action='SELECT')

            material_slots = material_idx_map[item.obj.data]
            print("MATERIAL-SLOTS:%s" % material_slots)
            for mat_slot_idx in material_slots:
                bpy.ops.object.mode_set(mode="EDIT",toggle=False)
                # deselect verices on mesh
                bpy.ops.mesh.select_all(action='DESELECT')
                
                if not rsettings.uv_split_multimaterial:
                    bpy.ops.mesh.select_all(action='SELECT') # if we don't split. one pass with all vertices is enough       

                # select material-slot
                bpy.context.object.active_material_index = mat_slot_idx
                # select all faces
                bpy.ops.object.material_slot_select()
                # and select them in the uv-editor
                bpy.ops.uv.select_all(action='SELECT')

                print("SLOT AMOUNT:%s valid_items:%s" % (tex_amount,len(valid_items)))
                if tex_amount>1:
                    # nothing to do if we only bake one uvmap
                    if len(valid_items)!=1:
                        bpy.ops.transform.resize(value=(scale, scale, scale), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False)
                    
                    if rsettings.uv_split_multimaterial and (pack_multi_material or len(valid_items)==1):
                        print("pack %s dt:%s" % (pack_multi_material,dt))
                        # pack: all material-textures on one slot.
                        x_step = dt / len(material_slots)
                        x_size = (1 / len(material_slots)) * 0.95 # (keep some distance between the sub-slots)

                        bpy.ops.transform.resize(value=(x_size , 1, 1), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', constraint_axis=(True, False, False), mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False)

                        bpy.ops.transform.translate(value=(pos_x, pos_y, 0), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False)
                        pos_x = pos_x + x_step
                        if pos_x >= 0.99:
                            pos_x = 0
                            pos_y = pos_y + dt                    
                    else:
                        print("no pack")
                        bpy.ops.transform.translate(value=(pos_x, pos_y, 0), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False)
                        pos_x = pos_x + dt
                        if pos_x >= 0.99:
                            pos_x = 0
                            pos_y = pos_y + dt                    

                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.uv.select_all(action='DESELECT')
                bpy.ops.object.mode_set(mode="OBJECT",toggle=False)            

                if not rsettings.uv_split_multimaterial:
                    # one pass is enough if you do not split the multimaterials
                    break

            # deselect obj
            print("TRY TO SELECT %s" %atlas_grp_idx)
            bpy.ops.simpleatlas.bake(atlasid=atlas_grp_idx,only_select=True)
            bpy.ops.object.mode_set(mode="OBJECT",toggle=True)            


            bpy.ops.object.mode_set(mode="EDIT",toggle=False)
            bpy.ops.mesh.select_all(action='SELECT')




        return{'FINISHED'}
    

# get the render uv
def GetRenderUV(mesh):
    for uv in mesh.uv_layers:
        if uv.active_render:
            return uv
    return None

class SimpleAtlasUVArrange(bpy.types.Panel):
    bl_idname = "UV_PT_uv_arrange"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Group Baker"
    bl_label ="Atlas Creator"
    

    #bl_options = {'DEFAULT_CLOSED'}
    
    # @classmethod
    # def poll(cls, context):
    #     return bpy.context.scene.render.engine=="CYCLES"     


    @classmethod
    def poll(cls, context):
        sima = context.space_data
        return sima and sima.mode=="UV"
        #return True

    def draw(self, context):
        settings = bpy.context.scene.world.atlasSettings

        layout = self.layout
        row = layout.row()
        row.prop_search(settings,"uv_rearrange_atlasname",settings,"atlas_groups",text="bake group")

        atlas_group,_ = GetAtlasGroupByName(settings.uv_rearrange_atlasname)

        if not atlas_group:
            return
    
        rsettings = atlas_group.uv_rearrange_settings
        
        row = layout.row()
        row.prop(rsettings,"uv_name",text="new uv-name")
        row = layout.row()
        row.prop(rsettings,"uv_split_multimaterial",text="separate multi-material uvmaps")
        if not rsettings.uv_split_multimaterial:
            row = layout.row()
            row.enabled=False
            row.label(text="(e.g. if uvmaps are colliding)")
        else:
            row = layout.row()
            row.label(icon="DECORATE")
            row.prop(rsettings,"uv_pack_multimaterial",text="pack multi-materials on one uv-slot")

        row = layout.row()
        row.prop(rsettings,"uv_name_overwrite",text="overwrite uv with same name?")
        row = layout.row()
        row.prop(rsettings,"uv_autoset_bakeuv",text="set new uv as bake-uv in bake group")

        row = layout.row()


        row = layout.row()
        if not rsettings.uv_name or rsettings.uv_name=="":
            col = row.column()
            col.enabled=False
            col.operator("simpleatlas.uv_arrange").pack_multi_material = rsettings.uv_pack_multimaterial
        else:
            row.operator("simpleatlas.uv_arrange")


        sima = context.space_data

        col = layout.column()

        col = layout.column()
        col.prop(sima, "cursor_location", text="Cursor Location")        

classes =(RearrangeSettings, AtlasGroupBakeItemSettings,AtlasGroupBakeItem,AtlasGroupItem,AtlasGroup,AtlasData
            # group item
            ,SIMPLEATLAS_UL_LIST_ATLASGROUP_ITEM,UL_SIMPLEATLAS_LIST_ATLASGROUPITEM_CREATE,UL_SIMPLEATLAS_LIST_ATLASGROUPITEM_DELETE,UL_SIMPLEATLAS_LIST_ATLASGROUPITEM_SELECT
            # bake item
            ,UL_SIMPLEATLAS_LIST_ATLASGROUPBAKEITEM_CREATE,UL_SIMPLEATLAS_LIST_ATLASGROUPBAKEITEM_DELETE
            # group
            ,UL_SIMPLEATLAS_LIST_ATLASGROUPS_CREATE,UL_SIMPLEATLAS_LIST_ATLASGROUPS_DELETE,UL_SIMPLEATLAS_LIST_ATLASGROUPS_MOVE
            # scene panel
            ,SimpleAtlasRenderUI,BakeAll
            # uv arranger
            ,SimpleAtlasUVArrange, Rearrange
            )

defRegister, defUnregister = bpy.utils.register_classes_factory(classes)

def register():
    defRegister()
    bpy.types.World.atlasSettings = bpy.props.PointerProperty(type=AtlasData)
    
def unregister():
    defUnregister()
    del bpy.types.World.atlasSettings
    