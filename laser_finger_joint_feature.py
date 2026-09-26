import typing
import sys
import logging
import dataclasses

import adsk.core
import adsk.fusion

from . import sane

app = adsk.core.Application.get()
ui = app.userInterface
logger = logging.getLogger(__name__)



class LaserFingerJointFeature(sane.CustomFeature):
    def __init__(self):
        defaultLengthUnits = "mm" # app.activeProduct.unitsManager.defaultLengthUnits
        parameters = [
            sane.SelectionParameterDefinition('face', 'Faces', "Faces on which the fingers are generated. One joint is created per face, in selection order.", ['Faces'], min_count=1, max_count=0, repeat=True),
            sane.ValueParameterDefinition('depth', "Finger depth", tooltip="Depth of the finger cutouts", unit=defaultLengthUnits, initial_expression="5mm", minimum_value=0, is_minimum_inclusive=False),
            sane.ValueParameterDefinition('preferred_width', "Preferred width", tooltip="A finger width close to this will be used", unit=defaultLengthUnits, initial_expression="25mm", minimum_value=0, is_minimum_inclusive=False),
            sane.IntegerParameterDefinition('min_fingers', 'Min. finger count', tooltip="Minimum number of fingers", min_value=1, max_value=50, step=1, initial_value=1),
            sane.IntegerParameterDefinition('max_fingers', 'Max. finger count', tooltip="Maximum number of fingers", min_value=1, max_value=50, step=1, initial_value=10),
            sane.BooleanParameterDefinition("begin_with_finger", "Begin with finger", tooltip="If checked, the pattern starts with a finger (material left standing). Otherwise it starts with a cutout.", initial_value=False),
            sane.ValueParameterDefinition('offset_begin', "Offset at the beginning", tooltip="Length at the start of the edge that is left uncut before the finger pattern begins.", unit=defaultLengthUnits, initial_expression="0", minimum_value=0, is_minimum_inclusive=True),
            sane.BooleanParameterDefinition("end_with_finger", "End with finger", tooltip="If checked, the pattern ends with a finger (material left standing). Otherwise it ends with a cutout.", initial_value=False),
            sane.ValueParameterDefinition('offset_end', "Offset at the end", tooltip="Length at the end of the edge that is left uncut after the finger pattern ends.", unit=defaultLengthUnits, initial_expression="0", minimum_value=0, is_minimum_inclusive=True),
        ]

        super().__init__(
            # Never change the id: saved designs refer to their features by it.
            id='laser-finger-feature', 
            name='Laser Finger Joint', 
            tooltip='Finger Joints for Laser Cutting', 
            icon_path="resources",
            boolean_operation=adsk.fusion.FeatureOperations.CutFeatureOperation,
            parameters = parameters)
        
    def __post_init__(self):
        super().__post_init__()
        self.add_to_toolbar("FusionSolidEnvironment", "SolidModifyPanel")

    def validate_parameters(self, params: dict[str, typing.Any]) -> bool:
        def validate_face_selection():
            face = params['face'][0]
            if face is None:
                # Face was invalidated due to the modifications applied by the preview.
                # Skip this verification step.
                return True
            if not isinstance(face, adsk.fusion.BRepFace):
                return False
            try:
                self.extract_face_geometry(face)
            except ValueError:
                return False
            # The face must also allow a finger pattern that satisfies the settings
            return self.choose_num_segments(params) is not None
        
        if params['depth'] <= 0:
            return False
        if params['preferred_width'] <= 0:
            return False
        if params['min_fingers'] < 1:
            return False
        if params['max_fingers'] < params['min_fingers']:
            return False
        if params['offset_begin'] < 0:
            return False
        if params['offset_end'] < 0:
            return False
        
        return validate_face_selection()

    def identify_target_body(self, params: dict[str, typing.Any]) -> adsk.fusion.BRepBody:
        # This feature is applied to the body of the selected face.
        face: adsk.fusion.BRepFace = params['face'][0]
        return face.body
    
    def generate_tool_body(self, params: dict[str, typing.Any]) -> adsk.fusion.BRepBody:
        logger.info(f"Generate Tool: {params}")
        face: adsk.fusion.BRepFace = params['face'][0]

        depth = params['depth']
        offset_begin = params['offset_begin']
        offset_end = params['offset_end']
        begin_with_finger = params['begin_with_finger']

        corner, long_axis, short_axis = self.extract_face_geometry(face)
        num_segments = self.choose_num_segments(params)

        eval = face.evaluator
        (_, param) = eval.getParameterAtPoint(corner)
        (_, normal) = eval.getNormalAtParameter(param)

        half_short_axis = short_axis.copy()
        half_short_axis.scaleBy(0.5)

        long_axis_normalized = long_axis.copy()
        long_axis_normalized.normalize()

        half_height = normal.copy()
        half_height.scaleBy(-depth / 2)

        available_length = long_axis.length - offset_begin - offset_end
        width = available_length / num_segments

        tempBrepMgr = adsk.fusion.TemporaryBRepManager.get()

        # Create bodies for the cutouts
        cutouts = []
        even_cutouts = not begin_with_finger
        for seg in range(num_segments):
            if even_cutouts != ((seg % 2) == 0):
                continue
            long_axis_center = long_axis_normalized.copy()
            long_axis_center.scaleBy(offset_begin + (seg + 0.5) * width)
            center = corner.copy()
            center.translateBy(long_axis_center)
            center.translateBy(half_short_axis)
            center.translateBy(half_height)
 
            orientedBoundingBox = adsk.core.OrientedBoundingBox3D.create(center, long_axis, short_axis, width, short_axis.length, depth)
            cutout_body = tempBrepMgr.createBox(orientedBoundingBox)
            cutouts.append(cutout_body)

        # Create one more body to connect them all
        connector_thickness = depth / 10
        half_height = normal.copy()
        half_height.scaleBy(connector_thickness / 2)
        center_long_axis = long_axis_normalized.copy()
        center_long_axis.scaleBy(offset_begin + available_length / 2)
        center = corner.copy()
        center.translateBy(center_long_axis)
        center.translateBy(half_short_axis)
        center.translateBy(half_height)
        orientedBoundingBox = adsk.core.OrientedBoundingBox3D.create(center, long_axis, short_axis, available_length, short_axis.length, connector_thickness)
        combined_body = tempBrepMgr.createBox(orientedBoundingBox)

        for body in cutouts:
            tempBrepMgr.booleanOperation(combined_body, body, adsk.fusion.BooleanTypes.UnionBooleanType)

        return combined_body

    @staticmethod
    def extract_face_geometry(face: adsk.fusion.BRepFace):
        """
        Returns the coordinates of the face that we'll create the fingers on.
        This also verifies that the face is a valid selection.

        Returns:
        - corner of the face
        - vector along the long edge of the face
        - vector along the short edge of the face

        Throws ValueError if the face does not fulfill the requirements.
        """
        if not isinstance(face.geometry, adsk.core.Plane):
            raise ValueError("Face must be flat")

        if len(face.loops) != 1:
            raise ValueError("Face cannot have holes")
        
        loop = face.loops[0]

        if not loop.isOuter:
            raise ValueError("Face must have an outer loop")
        
        co_edges = loop.coEdges
        
        if len(co_edges) != 4:
            raise ValueError("Face must have exactly four edges")
        
        # Extract the line geometries of the four edges
        edge_geometries: list[adsk.core.Line3D] = []
        for co_edge in co_edges:
            geometry = co_edge.edge.geometry
            if not isinstance(geometry, adsk.core.Line3D):
                raise ValueError("Face must have straight edges")
            if co_edge.isParamReversed:
                edge_geometries.append(adsk.core.Line3D.create(geometry.endPoint, geometry.startPoint))
            else:
                edge_geometries.append(geometry)
        
        # Check that edges are perpendicular
        for i in range(1, len(edge_geometries)):
            vector_back = edge_geometries[i - 1].endPoint.vectorTo(edge_geometries[i - 1].startPoint)
            vector_forward = edge_geometries[i].startPoint.vectorTo(edge_geometries[i].endPoint)
            if not vector_back.isPerpendicularTo(vector_forward):
                raise ValueError("Face edges must be perpendicular")

        # Order edge_geometries so that the longest edge is the first edge
        longest_edge_index = edge_geometries.index(max(edge_geometries, key=lambda e: e.startPoint.distanceTo(e.endPoint)))
        edge_geometries = edge_geometries[longest_edge_index:] + edge_geometries[:longest_edge_index]
        
        corner = edge_geometries[0].startPoint
        long_edge = edge_geometries[0].startPoint.vectorTo(edge_geometries[0].endPoint)
        short_edge = edge_geometries[-1].endPoint.vectorTo(edge_geometries[-1].startPoint)
        return corner, long_edge, short_edge
    
    @staticmethod
    def choose_num_segments(params: dict[str, typing.Any]) -> typing.Optional[int]:
        """
        A segment is either a finger or a gap between fingers.
        This function selects the number of segments.

        Returns None if no number of segments satisfies the parameters, e.g. because
        the offsets leave no room or the finger count limits can't be met.
        """

        face: adsk.fusion.BRepFace = params['face'][0]
        offset_begin = params['offset_begin']
        offset_end = params['offset_end']
        preferred_width = params['preferred_width']
        min_fingers = params['min_fingers']
        max_fingers = params['max_fingers']
        begin_with_finger = params['begin_with_finger']
        end_width_finger = params['end_with_finger']

        _, long_edge, _ = LaserFingerJointFeature.extract_face_geometry(face)
        edge_length = long_edge.length

        available_length = edge_length - offset_begin - offset_end
        if available_length <= 0:
            return None

        # Try every segment count that could satisfy the finger limits and pick the one whose
        # width is closest to the preferred width. With max_fingers fingers there are at most
        # 2 * max_fingers + 1 segments (when both ends are gaps), which bounds the search.
        must_be_even = begin_with_finger != end_width_finger
        best_num_segments = None
        best_diff = None
        for num_segments in range(2, 2 * max_fingers + 2):
            if ((num_segments % 2) == 0) != must_be_even:
                continue
            if begin_with_finger:
                num_fingers = (num_segments + 1) // 2
            else:
                num_fingers = num_segments // 2
            if not (min_fingers <= num_fingers <= max_fingers):
                continue
            diff = abs(available_length / num_segments - preferred_width)
            if best_diff is None or diff < best_diff:
                best_num_segments = num_segments
                best_diff = diff

        return best_num_segments