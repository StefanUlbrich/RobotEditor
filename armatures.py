import bpy, math, mathutils
from bpy.props import *


# creates a new armature, new_name is the name of the new armature
def createArmature(new_name) :
    armature_data = bpy.data.armatures.new(new_name)
    armature_Object = bpy.data.objects.new(new_name, armature_data)
    armature_Object.data = armature_data
    armature_data.show_names = True
    armature_data.show_axes = True
    armature_data.draw_type = 'STICK'
    #armature_data.use_deform_envelopes = False
    scene = bpy.context.scene
    scene.objects.link(armature_Object)
    return armature_Object

# creates new bone, armatureName identifies the armature, boneName the name of the new bone
# and parentName(optional) identifies the name of the parent bone
def createBone(armatureName, boneName, parentName = None):
    print("createBone")
    bpy.ops.roboteditor.selectarmature(armatureName = armatureName)
    currentMode = bpy.context.object.mode

    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    #arm = bpy.data.armatures[armatureName]
    bone = bpy.data.armatures[armatureName].edit_bones.new(boneName)
    bone.head = (0,0,0) #Dummy
    bone.tail = (0,0,1) #Dummy
    bone.lock = True

    if not parentName == None:
        bone.parent = bpy.data.armatures[armatureName].edit_bones[parentName]


    bpy.ops.object.mode_set(mode='POSE', toggle = False)

    bpy.ops.roboteditor.selectbone(boneName=boneName)
    bpy.ops.pose.constraint_add(type='LIMIT_ROTATION')
    bpy.context.object.pose.bones[boneName].constraints[0].name='RobotEditorConstraint'
    bpy.ops.object.mode_set(mode=currentMode, toggle=False)
    print("createBone done")


# Function to convert a given rotation vector and a roll angle anlong this axis into a 3x3 rotation matrix
# Python port of the C function defined in armature.c
# Thanks to blenderartists.org user vida_vida
def _vec_roll_to_mat3(vec, roll):
    target = mathutils.Vector((0,1,0))
    nor = vec.normalized()
    axis = target.cross(nor)
    if axis.dot(axis) > 0.0000000001: # this seems to be the problem for some bones, no idea how to fix
        axis.normalize()
        theta = target.angle(nor)
        bMatrix = mathutils.Matrix.Rotation(theta, 3, axis)
    else:
        updown = 1 if target.dot(nor) > 0 else -1
        bMatrix = mathutils.Matrix.Scale(updown, 3)

        # C code:
        #bMatrix[0][0]=updown; bMatrix[1][0]=0.0;    bMatrix[2][0]=0.0;
        #bMatrix[0][1]=0.0;    bMatrix[1][1]=updown; bMatrix[2][1]=0.0;
        #bMatrix[0][2]=0.0;    bMatrix[1][2]=0.0;    bMatrix[2][2]=1.0;
        bMatrix[2][2] = 1.0

    rMatrix = mathutils.Matrix.Rotation(roll, 3, nor)
    mat = rMatrix * bMatrix
    return mat


# Function to convert a 3x3 rotation matrix to a rotation axis and a roll angle along this axis
# Python port of the C function defined in armature.c
# Thanks to blenderartists.org user vida_vida
def _mat3_to_vec_roll(mat):

    vec = mat.col[1] * bpy.context.scene.RobotEditor.boneLength
    vecmat = _vec_roll_to_mat3(mat.col[1], 0)
    vecmatinv = vecmat.inverted()
    rollmat = vecmatinv * mat
    roll = math.atan2(rollmat[0][2], rollmat[2][2])
    return vec, roll

# update kinematics chain of armatureName starting with boneName
def updateKinematics(armatureName, boneName=None):
    #    print("updateKinematics")
    currentMode = bpy.context.object.mode

    #arm = bpy.data.armatures[armatureName]

    if not boneName is None:
        boneName = bpy.data.armatures[armatureName].bones[boneName].name
    else:
        boneName = bpy.data.armatures[armatureName].bones[0].name

    #local variables for updating the constraints
    jointAxis = bpy.data.armatures[armatureName].bones[boneName].RobotEditor.axis
    min_rot = bpy.data.armatures[armatureName].bones[boneName].RobotEditor.theta.min
    max_rot = bpy.data.armatures[armatureName].bones[boneName].RobotEditor.theta.max
    jointMode =bpy.data.armatures[armatureName].bones[boneName].RobotEditor.jointMode
    jointValue = bpy.data.armatures[armatureName].bones[boneName].RobotEditor.theta.value


    matrix, jointMatrix = bpy.data.armatures[armatureName].bones[boneName].RobotEditor.getTransform()

    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    edit_bone = bpy.data.armatures[armatureName].edit_bones[bpy.data.armatures[armatureName].bones[boneName].name]
    edit_bone.use_inherit_rotation = True

    if not edit_bone.parent is None:
        transform = edit_bone.parent.matrix.copy()
        matrix = transform * matrix

    pos = matrix.to_translation()
    axis, roll = _mat3_to_vec_roll(matrix.to_3x3())

    edit_bone.head = pos
    edit_bone.tail = pos+axis
    edit_bone.roll = roll

    bpy.ops.object.mode_set(mode=currentMode, toggle = False)

    # update pose
    bpy.ops.object.mode_set(mode='POSE', toggle = False)
    #pose_bone = bpy.context.active_pose_bone
    pose_bone = bpy.context.object.pose.bones[boneName]
#    print (pose_bone.name, jointMatrix)
    pose_bone.matrix_basis = jointMatrix

    # Adding constraints for revolute joints
    #---------- REMOVED DUE TO BUG IN BLENDER ------------
    #if jointMode == 'REVOLUTE':
    #    if 'RobotEditorConstraint' in pose_bone.constraints:
    #        constraint = [i for i in pose_bone.constraints if i.type == 'LIMIT_ROTATION'][0]
    #        constraint.name = 'RobotEditorConstraint'
    #        constraint.owner_space='LOCAL'
    #        constraint.use_limit_x=True
    #        constraint.use_limit_y=True
    #        constraint.use_limit_z=True
    #        constraint.min_x=0.0
    #        constraint.min_y=0.0
    #        constraint.min_z=0.0
    #        constraint.max_x=0.0
    #        constraint.max_y=0.0
    #        constraint.max_z=0.0
    #        print(math.radians(jointValue))
    #        print(math.radians(min_rot),math.radians(max_rot))
    #        if jointAxis=='X':
    #            constraint.min_x=math.radians(min_rot)
    #            constraint.max_x=math.radians(max_rot)
    #        elif jointAxis=='Y':
    #            constraint.min_y=math.radians(min_rot)
    #            constraint.max_y=math.radians(max_rot)
    #        elif jointAxis=='Z':
    #            constraint.min_z=math.radians(min_rot)
    #            constraint.max_z=math.radians(max_rot)
    #-------------------------------------------------------
    bpy.ops.object.mode_set(mode=currentMode, toggle = False)

    #   print("Number of children")
    #   print(len(arm.bones[boneName].children))
    #   print("updateKinematics Done")
    # recursive call on all children
    childBoneNames = [i.name for i in bpy.data.armatures[armatureName].bones[boneName].children]
#   print(boneName,childBoneNames)
    for childBoneName in childBoneNames:
#        if childBoneName == "":
#            print('Empty name',childBoneName,childBoneNames,boneName)
        updateKinematics(armatureName, childBoneName)

    #TODO: Add constraints!

# operator to select armature
class RobotEditor_selectArmature(bpy.types.Operator):
    bl_idname = "roboteditor.selectarmature"
    bl_label = "Select Armature"

    armatureName = StringProperty()

    def execute(self, context):
        for obj in bpy.data.objects :
            obj.select = False

        context.scene.objects.active = bpy.data.objects[self.armatureName]
        context.active_object.select = True
        context.scene.RobotEditor.armatureName = self.armatureName # not so sure if this is needed at all

        if len(context.active_object.data.bones) > 0 :
            baseBoneName = context.active_object.data.bones[0].name
            bpy.ops.roboteditor.selectbone(boneName = baseBoneName)
        return{'FINISHED'}


# operator to create armature
class RobotEditor_createArmature(bpy.types.Operator):
    bl_idname = "roboteditor.createarmature"
    bl_label = "Create Armature"

    armatureName = StringProperty(name="Enter armature name:")
    baseBoneName = StringProperty(name="Enter base bone name:")

    def execute(self,context):
        createArmature(self.armatureName)
        bpy.ops.roboteditor.selectarmature(armatureName = self.armatureName)
        bpy.ops.roboteditor.createbone(boneName = self.baseBoneName)

        return{'FINISHED'}


    def invoke(self, context, event) :
        return context.window_manager.invoke_props_dialog(self)


# menu to select exisiting armature or create new one
class RobotEditor_ArmatureMenu(bpy.types.Menu) :
    bl_idname = "roboteditor.armaturemenu"
    bl_label = "Selecht Armature"

    def draw(self, context):
        layout = self.layout
        armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']

        layout.operator("roboteditor.createarmature", text="New...")

        for arm in armatures:
            text = arm.name
            layout.operator("roboteditor.selectarmature", text=text).armatureName=text


# operator to rename selected armature
class RobotEditor_renameArmature(bpy.types.Operator) :
    bl_idname = "roboteditor.renamearmature"
    bl_label = "Rename selected armature"

    newName = StringProperty(name="Enter new name:")

    def execute(self, context):
        oldName = context.active_object.name
        context.active_object.name = self.newName
        bpy.data.armatures[oldName].name = self.newName

        return{'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


# operator to join 2 armatures
class RobotEditor_joinArmature(bpy.types.Operator):
    bl_idname = "roboteditor.joinarmature"
    bl_label = "Join 2 Armatures"

    targetArmatureName = StringProperty()

    def execute(self, context):
        sourceArmName = context.active_object.name
        sourceParentBoneName = context.active_object.data.bones[0].name
        bpy.ops.roboteditor.selectarmature(armatureName=self.targetArmatureName)
        bpy.data.objects[sourceArmName].select = True

        bpy.ops.object.join()
        bpy.ops.roboteditor.selectbone(boneName = sourceParentBoneName)
        bpy.ops.roboteditor.assignparentbone(parentName = context.active_object.data.bones[0].name)

        updateKinematics(context.active_object.name, sourceParentBoneName)
        return{'FINISHED'}

# dynamic menu for joining two armatures
class RobotEditor_ArmatureJoinMenu(bpy.types.Menu):
    bl_idname = "roboteditor.joinarmaturemenu"
    bl_label = "Join selected armature with different armature"

    def draw(self, context):
        layout = self.layout

        currentName = context.active_object.data.name
        armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE' and not obj.name == currentName]

        for arm in armatures:
            text = arm.name
            layout.operator("roboteditor.joinarmature", text=text).targetArmatureName = text



# draw method that builds the part of the GUI responsible for the armature
def draw(layout, context):
    armatureSelected = False
    layout.label(text="Select Armature:")
    try:
        if context.active_object.type == 'ARMATURE':
            armatureSelected = True
            row = layout.row(align=True)
            row.menu("roboteditor.armaturemenu", text=context.active_object.name)
            row.separator()
            row.operator("roboteditor.renamearmature")

            layout.label(text="Merge with another armature")
            layout.menu("roboteditor.joinarmaturemenu", text = "")
        else:
            layout.menu("roboteditor.armaturemenu", text="")
            layout.label(text="Select Armature first")
    except:
        layout.menu("roboteditor.armaturemenu", text="")
        layout.label(text="Select Armature first")

    return armatureSelected



def register():
    bpy.utils.register_class(RobotEditor_selectArmature)
    bpy.utils.register_class(RobotEditor_createArmature)
    bpy.utils.register_class(RobotEditor_ArmatureMenu)
    bpy.utils.register_class(RobotEditor_renameArmature)
    bpy.utils.register_class(RobotEditor_joinArmature)
    bpy.utils.register_class(RobotEditor_ArmatureJoinMenu)

def unregister():
    bpy.utils.unregister_class(RobotEditor_selectArmature)
    bpy.utils.unregister_class(RobotEditor_createArmature)
    bpy.utils.unregister_class(RobotEditor_ArmatureMenu)
    bpy.utils.unregister_class(RobotEditor_renameArmature)
    bpy.utils.unregister_class(RobotEditor_joinArmature)
    bpy.utils.unregister_class(RobotEditor_ArmatureJoinMenu)
