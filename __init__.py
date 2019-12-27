found_blender = False
try:
    import bpy
except:
    pass

bl_info = {
    "name": "Simple Atlas",
    "description": "creates simple atlas for multiple objects",
    "author": "Thomas Trocha",
    "version": (0, 0, 1),
    "blender": (2, 80, 0),
    "location": "View3D",
    "warning": "This addon is still in development.",
    "wiki_url": "",
    "category": "Object" }


def mesh_object_poll(self,object):
    return object.type=="MESH"
    
class AtlasGroupItem(bpy.types.PropertyGroup):
    obj : bpy.props.PointerProperty(type=bpy.types.Object,poll=mesh_object_poll)
    atlas_uv : bpy.props.IntProperty(default=0)
    #atlas_uv : bpy.props.PointerProperty(type=bpy.types.MeshUVLoopLayer)



class AtlasGroup(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty(default="noname")
    show_details : bpy.props.BoolProperty()
    atlas_items : bpy.props.CollectionProperty(type=AtlasGroupItem)
    diffuse : bpy.props.PointerProperty(type=bpy.types.Image)
    normal : bpy.props.PointerProperty(type=bpy.types.Image)
    selection_idx : bpy.props.IntProperty()

class AtlasData(bpy.types.PropertyGroup):
    atlas_groups : bpy.props.CollectionProperty(type=AtlasGroup)
    selection_idx : bpy.props.IntProperty()


##############################################
##              Atlas-Group
##############################################

#######
# items
#######
class UL_SIMPLEATLAS_LIST_ATLASGROUP_ITEM(bpy.types.UIList):
    """Atlasgroup UIList."""

    def draw_item(self, context, layout, data, item, icon, active_data,active_propname, index):
        custom_icon = 'NODETREE' # TODO

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            row.prop(item,"obj")
            if item.obj:
                row = layout.row()
                row.prop(item,"atlas_uv")
                #row.template_list("MESH_UL_uvmaps", "uvmaps", item.obj.data, "uv_layers", item, "atlas_uv", rows=1)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon = custom_icon)

class UL_SIMPLEATLAS_LIST_ATLASGROUPITEM_CREATE(bpy.types.Operator):
    """Add a new item to the list."""

    bl_idname = "simpleatlas.create_group_item"
    bl_label = "Add a new atlas group"

    atlas_group_idx = bpy.props.IntProperty()

    def execute(self, context):
        context.scene.world.atlasSettings.atlas_groups[self.atlas_group_idx].atlas_items.add()
        return{'FINISHED'}

class UL_SIMPLEATLAS_LIST_ATLASGROUPITEM_DELETE(bpy.types.Operator):
    """Add a new item to the list."""

    bl_idname = "simpleatlas.delete_group_item"
    bl_label = "Add a new atlas group"

    atlas_group_idx = bpy.props.IntProperty()

    def execute(self, context):
        group = context.scene.world.atlasSettings.atlas_groups[self.atlas_group_idx]
        index = group.selection_idx
        group.atlas_items.remove(index)
        group.selection_idx = min(max(0, index - 1), len(group.atlas_items) - 1)
        return{'FINISHED'}

########
# groups
########
class UL_SIMPLEATLAS_LIST_ATLASGROUPS_CREATE(bpy.types.Operator):
    """Add a new item to the list."""

    bl_idname = "simpleatlas.create_group"
    bl_label = "Add a new atlas group"

    def execute(self, context):
        context.scene.world.atlasSettings.atlas_groups.add()
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
        context.active_object.list_index_userdata = min(max(0, self.index - 1), len(atlasGroupList) - 1)
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

    @classmethod
    def poll(cls, context):
        return True

    def bake(self,context,atlasgroup):

        if (not atlasgroup.diffuse and not atlasgroup.normal):
            print("atlas group:%s had neither diffuse nor normal-images set! Skipping")
            return

        # keep track of materials in which we set an image-texture
        handled_materials = []

        created_nodes = []

        # deselect all objects
        bpy.ops.object.select_all(action='DESELECT')

        for item in atlasgroup.atlas_items:
            if not item.obj:
                continue

            # select the object
            item.obj.select_set(state=True)

            # set active uvmaps to the atlas ones
            item.obj.data.uv_layers.active_index = item.atlas_uv

            for mat_slot in item.obj.material_slots:
                if mat_slot.material in handled_materials:
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

        if atlasgroup.diffuse:
            # bake diffuse

            # set bake-mode to diffuse
            bpy.context.scene.cycles.bake_type = 'DIFFUSE'
            # set the diffuse texture to all temp-imageTexNodes
            for imgTexNode in created_nodes:
                imgTexNode.image = atlasgroup.diffuse
            
            # bake
            #bpy.ops.object.bake()

#             bpy.ops.object.bake('INVOKE_DEFAULT',type="DIFFUSE")
            bpy.ops.object.bake(type="DIFFUSE")

        if atlasgroup.normal:
            # bake diffuse

            # set the diffuse texture to all temp-imageTexNodes
            for imgTexNode in created_nodes:
                imgTexNode.image = atlasgroup.normal
            
            bpy.ops.object.bake(type="NORMAL")


        # cleanup
        
        # remove nodes from its nodetree
        for node in created_nodes:
            node.id_data.nodes.remove(node)

        handled_materials.clear()
        created_nodes.clear()



    def execute(self, context):
        atlasGroupList = context.scene.world.atlasSettings.atlas_groups

        if self.atlasid==-1:
            for atlas_group in atlasGroupList:
                self.bake(context,atlas_group)
        else:
            bakeGrp = atlasGroupList[self.atlasid]
            self.bake(context,bakeGrp)
        return{'FINISHED'}


class SimpleAtlasRenderUI(bpy.types.Panel):
    bl_idname = "RENDER_PT_simple_atlas"
    bl_label = "Simple Atlas"
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

            row = box.row()
            if atlas_group.show_details:
                row.prop(atlas_group,"name")
            else:
                row.label(text=atlas_group.name)

            row.prop(atlas_group,"show_details",text="details")

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
                row.template_list("UL_SIMPLEATLAS_LIST_ATLASGROUP_ITEM","The_list",atlas_group,"atlas_items",atlas_group,"selection_idx")
                row = box.row()
                row.operator('simpleatlas.create_group_item', text='NEW').atlas_group_idx=idx
                row.operator('simpleatlas.delete_group_item', text='DEL').atlas_group_idx=idx
                #row = layout.row()

                row = box.row()
                row.prop(atlas_group,"diffuse")
                row = box.row()
                row.prop(atlas_group,"normal")

                row = box.row()
                row.operator('simpleatlas.bake',text="bake group").atlasid=idx

            idx = idx + 1

        box = layout.box()
        row = box.row()

        row.operator('simpleatlas.create_group', text='NEW BAKE GROUP',icon="MONKEY")

        row = box.row()
        row.operator('simpleatlas.bake',text="bake all").atlasid=-1

classes =(AtlasGroupItem,AtlasGroup,AtlasData
            ,UL_SIMPLEATLAS_LIST_ATLASGROUP_ITEM,UL_SIMPLEATLAS_LIST_ATLASGROUPITEM_CREATE,UL_SIMPLEATLAS_LIST_ATLASGROUPITEM_DELETE
            ,UL_SIMPLEATLAS_LIST_ATLASGROUPS_CREATE,UL_SIMPLEATLAS_LIST_ATLASGROUPS_DELETE,UL_SIMPLEATLAS_LIST_ATLASGROUPS_MOVE
            ,SimpleAtlasRenderUI
            ,BakeAll)

defRegister, defUnregister = bpy.utils.register_classes_factory(classes)

def register():
    defRegister()
    bpy.types.World.atlasSettings = bpy.props.PointerProperty(type=AtlasData)
    
def unregister():
    defUnregister()
    del bpy.types.World.atlasSettings
    