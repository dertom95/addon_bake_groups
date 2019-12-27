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

class AtlasGroupItem(bpy.types.PropertyGroup):
    obj : bpy.props.PointerProperty(type=bpy.types.Object,poll=mesh_object_poll)
    atlas_uv : bpy.props.EnumProperty(items=AtlasGroupItemUVCallback, description="UVMap used for baking")

bake_types = [(bt,bt,bt) for bt in ['COMBINED', 'AO', 'SHADOW', 'NORMAL', 'UV', 'EMIT', 'ENVIRONMENT', 'DIFFUSE', 'GLOSSY', 'TRANSMISSION', 'SUBSURFACE']]

class AtlasGroupBakeItem(bpy.types.PropertyGroup):
    bake_type : bpy.props.EnumProperty(items=bake_types)
    image : bpy.props.PointerProperty(type=bpy.types.Image)

class AtlasGroup(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty(default="noname")
    show_details : bpy.props.BoolProperty()
    atlas_items : bpy.props.CollectionProperty(type=AtlasGroupItem)
    bake_items: bpy.props.CollectionProperty(type=AtlasGroupBakeItem)
    #diffuse : bpy.props.PointerProperty(type=bpy.types.Image)
    #normal : bpy.props.PointerProperty(type=bpy.types.Image)
    selection_idx : bpy.props.IntProperty()
    bake_selection_idx : bpy.props.IntProperty()

class AtlasData(bpy.types.PropertyGroup):
    atlas_groups : bpy.props.CollectionProperty(type=AtlasGroup)
    selection_idx : bpy.props.IntProperty()


##############################################
##              Atlas-Group
##############################################

###################
# atlas group items (object/uv)
###################
class UL_SIMPLEATLAS_LIST_ATLASGROUP_ITEM(bpy.types.UIList):
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
                        row.prop(item,"atlas_uv",text="uv")
                    else:
                        row.prop(item,"atlas_uv",text="uv",icon="ERROR")
                
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

        # iterate over all bake-items and bake them
        for bake_item in atlasgroup.bake_items:
            if not bake_item.image:
                print("no image for bake_type:%s" % bake_item.bake_type)
                continue

            # set the texture to all temp-imageTexNodes
            for imgTexNode in created_nodes:
                imgTexNode.image = bake_item.image
            
            # bake
            print("bake %s" % bake_item.bake_type)
            bpy.ops.object.bake(type=bake_item.bake_type)




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
            
            if atlas_group.show_details:
                row = box.row()
                row.label(text="Bake Atlas")
                row = box.row()
                row.prop(atlas_group,"name")
            else:
                row = box.row()
                row.label(text=atlas_group.name)

            row.prop(atlas_group,"show_details",text="details")

            row.operator('simpleatlas.bake',text="bake").atlasid=idx

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
                row.operator('simpleatlas.create_group_item', text='add object').atlas_group_idx=idx
                row.operator('simpleatlas.delete_group_item', text='del').atlas_group_idx=idx
                box.separator()

                #row = layout.row()
                bake_item_idx=0
                for bake_item in atlas_group.bake_items:
                    row = box.row()
                    row.prop(bake_item,"bake_type")
                    if bake_item.image:
                        row.prop(bake_item,"image")
                    else:
                        row.prop(bake_item,"image",icon="ERROR")

                    op = row.operator('simpleatlas.delete_bake_item', text="", icon="X")
                    op.atlas_group_idx=idx
                    op.index=bake_item_idx
                    bake_item_idx = bake_item_idx + 1

                row = box.row()
                row.operator('simpleatlas.create_bake_item', text='add bake-type').atlas_group_idx=idx


                #row.prop(atlas_group,"diffuse")
                #row = box.row()
                #row.prop(atlas_group,"normal")


            idx = idx + 1
            if atlas_group.show_details:
                layout.separator()


        box = layout.box()
        row = box.row()

        row.operator('simpleatlas.create_group', text='NEW BAKE GROUP',icon="MONKEY")

        row = box.row()
        row.operator('simpleatlas.bake',text="bake all groups").atlasid=-1

classes =(AtlasGroupBakeItem,AtlasGroupItem,AtlasGroup,AtlasData
            # group item
            ,UL_SIMPLEATLAS_LIST_ATLASGROUP_ITEM,UL_SIMPLEATLAS_LIST_ATLASGROUPITEM_CREATE,UL_SIMPLEATLAS_LIST_ATLASGROUPITEM_DELETE
            # bake item
            ,UL_SIMPLEATLAS_LIST_ATLASGROUPBAKEITEM_CREATE,UL_SIMPLEATLAS_LIST_ATLASGROUPBAKEITEM_DELETE
            # group
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
    