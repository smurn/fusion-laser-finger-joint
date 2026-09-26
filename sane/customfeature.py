import typing
import dataclasses
import enum
import logging
import itertools
import sys

import adsk.core
import adsk.fusion
from .event_utils import register_event_handler
from . import utils

app = adsk.core.Application.get()
ui = app.userInterface
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

"""
default app params
create input from app params
generate app params from inputs
create feature params and deps from inputs
set feature params from app params but with expressions
"""


class ExpressionType(enum.Enum):
    Number = enum.auto()
    String = enum.auto()
    Entity = enum.auto()


class ParameterDefinition[Value, Expression]:

    def __init__(self, id: str, unit: str, expression_type: ExpressionType, value_type: type, inital_expression: Expression):
        self.id = id
        self.unit = unit
        self.expression_type = expression_type
        self.value_type = value_type
        self.inital_expression = inital_expression

    def create_and_add_command_input(self, command_inputs: adsk.core.CommandInputs) -> adsk.core.CommandInput:
        """
        Creates a command input by adding it to the given command inputs.
        """
        raise NotImplementedError('abstract')
    
    def update_command_input_from_expression(self, command_input: adsk.core.CommandInput, expression: Expression):
        """
        Changes the current expression of the given command input.
        """
        raise NotImplementedError('abstract')
    
    def value(self, command_input: adsk.core.CommandInput) -> Value:
        """
        Returns the current value of the given command input.
        """
        raise NotImplementedError('abstract')

    def expression(self, command_input: adsk.core.CommandInput) -> Expression:
        """
        Returns the current expression of the given command input.
        """
        raise NotImplementedError('abstract')

    def remember(self, command_input: adsk.core.CommandInput) -> typing.Any:
        """
        Captures the current state of the given command input so that it can be
        restored later with restore(). Used to pre-fill the dialog with the last used settings.
        """
        return self.expression(command_input)

    def restore(self, command_input: adsk.core.CommandInput, remembered: typing.Any):
        """
        Restores a state previously captured with remember().
        """
        self.update_command_input_from_expression(command_input, remembered)


class SelectionParameterDefinition(ParameterDefinition[list[adsk.core.Base], list[adsk.core.Base]]):
    def __init__(self, id: str, name: str, tooltip: str, selection_filters: list[str], min_count: int, max_count: int, repeat: bool = False):
        """
        max_count: Maximum number of selected entities. 0 means unlimited.
        repeat: If True, the create dialog accepts multiple entities and one feature instance is created
                per selected entity, applied in selection order. Each instance sees a list with exactly one
                entity for this parameter. The edit dialog only accepts one entity.
                At most one parameter of a feature can have this set.
        """
        super().__init__(
            id=id,
            unit="",
            expression_type=ExpressionType.Entity,
            value_type=list,
            inital_expression=[])
        self.name = name
        self.tooltip = tooltip
        self.selection_filters = selection_filters
        self.min_count = min_count
        self.max_count = max_count
        self.repeat = repeat

    def create_and_add_command_input(self, command_inputs: adsk.core.CommandInputs) -> adsk.core.CommandInput:
        command_input = command_inputs.addSelectionInput(self.id, self.name, self.tooltip)
        command_input.setSelectionLimits(self.min_count, self.max_count)
        for filter in self.selection_filters:
            assert command_input.addSelectionFilter(filter)
        return command_input
    
    def update_command_input_from_expression(self, command_input: adsk.core.CommandInput, expression: list[adsk.core.Base]):
        command_input: adsk.core.SelectionCommandInput = command_input
        command_input.clearSelection()
        if expression:
            for entity in expression:
                if entity is None or not entity.isValid:
                    # Lost reference, e.g. an upstream change removed the entity. Leave the selection
                    # empty so the user can pick a replacement.
                    logger.warning(f"{self.name}: skipping a selection that no longer exists")
                    continue
                if not command_input.addSelection(entity):
                    logger.warning(f"{self.name}: unable to select {entity}")

    def value(self, command_input: adsk.core.CommandInput) -> list[adsk.core.Base]:
        command_input: adsk.core.SelectionCommandInput = command_input
        return [command_input.selection(i).entity for i in range(command_input.selectionCount)]
    
    def expression(self, command_input: adsk.core.CommandInput) -> list[adsk.core.Base]:
        return self.value(command_input)
    
    def as_dependencies(self, entities: list[adsk.core.Base]) -> list[tuple[str, adsk.core.Base]]:
        return [(f"{self.id}-{i}", entity) for i, entity in enumerate(entities)]
    
    def from_dependencies(self, dependencies: adsk.fusion.CustomFeatureDependencies) -> list[adsk.core.Base]:
        index_entry = []
        for dep in dependencies:
            dep_id, index = dep.id.rsplit('-', 1)
            if dep_id != self.id:
                continue
            index_entry.append((int(index), dep.entity))
        index_entry.sort()
        return [e for _, e in index_entry]


class ValueParameterDefinition(ParameterDefinition[float, str]):
    def __init__(self, id: str, name: str, tooltip: str, unit:str, initial_expression: str,
                  minimum_value:float=-sys.float_info.max,
                  is_minimum_inclusive: bool = True,
                  maximum_value:float=sys.float_info.max,
                  is_maximum_inclusive: bool = True):
        super().__init__(
            id=id, 
            unit=unit, 
            expression_type=ExpressionType.String,
            value_type=float,
            inital_expression=initial_expression)
        self.name = name
        self.tooltip = tooltip
        self.minimum_value = minimum_value
        self.is_minimum_inclusive = is_minimum_inclusive
        self.maximum_value = maximum_value
        self.is_maximum_inclusive = is_maximum_inclusive

    def create_and_add_command_input(self, command_inputs: adsk.core.CommandInputs) -> adsk.core.CommandInput:
        command_input = command_inputs.addValueInput(self.id, self.name, self.unit, adsk.core.ValueInput.createByString(self.inital_expression))
        command_input.tooltip = self.tooltip

        command_input.minimumValue = self.minimum_value
        command_input.isMinimumInclusive = self.is_minimum_inclusive
        command_input.isMinimumLimited = self.minimum_value > -sys.float_info.max
        
        command_input.maximumValue = self.maximum_value
        command_input.isMaximumInclusive = self.is_maximum_inclusive
        command_input.isMaximumLimited = self.maximum_value < sys.float_info.max
        return command_input
    
    def update_command_input_from_expression(self, command_input: adsk.core.CommandInput, expression: str):
        command_input: adsk.core.ValueCommandInput = command_input
        command_input.expression = expression


    def value(self, command_input: adsk.core.CommandInput) -> list[adsk.core.Base]:
        command_input: adsk.core.ValueCommandInput = command_input
        return command_input.value
    
    def expression(self, command_input: adsk.core.CommandInput) -> list[adsk.core.Base]:
        command_input: adsk.core.ValueCommandInput = command_input
        return command_input.expression

    def remember(self, command_input: adsk.core.CommandInput) -> tuple[str, float]:
        # Keep both the expression (to preserve references to user parameters)
        # and the evaluated value (fallback if the expression isn't valid in another design).
        command_input: adsk.core.ValueCommandInput = command_input
        return (command_input.expression, command_input.value)

    def restore(self, command_input: adsk.core.CommandInput, remembered: tuple[str, float]):
        command_input: adsk.core.ValueCommandInput = command_input
        expression, value = remembered
        units_manager = app.activeProduct.unitsManager
        if units_manager.isValidExpression(expression, self.unit):
            command_input.expression = expression
        else:
            # E.g. the expression references a user parameter that doesn't exist in this design.
            command_input.value = value


class BooleanParameterDefinition(ParameterDefinition[bool, float]):
    
    def __init__(self, id: str, name: str, tooltip: str, initial_value: bool):
        super().__init__(
            id=id, 
            unit="", 
            expression_type=ExpressionType.Number,
            value_type=bool,
            inital_expression=int(initial_value))
        self.name = name
        self.tooltip = tooltip

    def create_and_add_command_input(self, command_inputs: adsk.core.CommandInputs) -> adsk.core.CommandInput:
        command_input = command_inputs.addBoolValueInput(self.id, self.name, True, '')
        command_input.tooltip = self.tooltip
        return command_input

    def update_command_input_from_expression(self, command_input: adsk.core.CommandInput, expression: float):
        command_input: adsk.core.BoolValueCommandInput = command_input
        command_input.value = bool(expression)

    def value(self, command_input: adsk.core.CommandInput) -> bool:
        command_input: adsk.core.BoolValueCommandInput = command_input
        return command_input.value

    def expression(self, command_input: adsk.core.CommandInput) -> float:
        return float(self.value(command_input))


class IntegerParameterDefinition(ParameterDefinition[int, float]):
    def __init__(self, id: str, name: str, tooltip: str, min_value:int, max_value:int, step:int, initial_value: int):
        super().__init__(
            id=id, 
            unit="", 
            expression_type=ExpressionType.Number,
            value_type=int,
            inital_expression=float(initial_value))
        self.name = name
        self.tooltip = tooltip 
        self.min_value = min_value
        self.max_value = max_value
        self.step = step

    def create_and_add_command_input(self, command_inputs: adsk.core.CommandInputs) -> adsk.core.CommandInput:
        command_input = command_inputs.addIntegerSpinnerCommandInput(self.id, self.name, min=self.min_value, max=self.max_value, spinStep=self.step, initialValue=int(self.inital_expression))
        command_input.tooltip = self.tooltip
        return command_input

    def update_command_input_from_expression(self, command_input: adsk.core.CommandInput, expression: float):
        command_input: adsk.core.IntegerSpinnerCommandInput = command_input
        command_input.value = int(expression)

    def value(self, command_input: adsk.core.CommandInput) -> int:
        command_input: adsk.core.IntegerSpinnerCommandInput = command_input
        return command_input.value

    def expression(self, command_input: adsk.core.CommandInput) -> float:
        return float(self.value(command_input))

@dataclasses.dataclass
class CustomFeature:

    id: str
    name: str
    tooltip: str
    icon_path: str
    boolean_operation: adsk.fusion.FeatureOperations = adsk.fusion.FeatureOperations.JoinFeatureOperation
    show_preview: bool = True
    parameters: list[ParameterDefinition] = dataclasses.field(default_factory=list)

    class _Status(enum.Enum):
        #: No command is active.
        Inactive = 'Inactive'
        #: We are in the process of creating a new feature
        Creating = 'Creating'
        #: We are in the process of editing an existing feature.
        Editing = 'Editing'

    _create_command_definition: adsk.core.CommandDefinition = dataclasses.field(default=None, init=False)
    _edit_command_definition: adsk.core.CommandDefinition = dataclasses.field(default=None, init=False)
    _toolbar_control: adsk.core.ToolbarControls = dataclasses.field(default=None, init=False)
    _custom_feature_definition: adsk.fusion.CustomFeatureDefinition = dataclasses.field(default=None, init=False)

    #: Event handlers that are only unregistered when this custom feature is deleted.
    _permanent_handlers: list = dataclasses.field(default_factory=list, init=False)

    #: Current status of this feature
    _status: _Status = dataclasses.field(default=_Status.Inactive, init=False)

    #: Currently active command (dialog with input fields). This is set when creating a new instance of the custom feature
    #: or when editing an existing instance. In inactive state, it is None.
    _current_command: adsk.core.Command = dataclasses.field(default=None, init=False)

    #: List of commands handlers of the current command.
    _current_command_handlers: list = dataclasses.field(default_factory=list, init=False)

    #: If we are currently editing, then this holds the reference to the custom feature we're editing.
    _currently_edited_feature: adsk.fusion.CustomFeature = dataclasses.field(default=None, init=False)

    #: When editing a feature, we temporarily move the timeline marker. This is the reference to the origional position
    #: So that we can move the marker back.
    #: Object on the timeline left of the place where the marker used to be.
    #: This is None if we haven't moved the timeline.
    _original_timeline_position: adsk.fusion.TimelineObject = dataclasses.field(default=None, init=False)

    #: Settings of the last confirmed (OK) create or edit dialog, keyed by parameter id.
    #: Used to pre-fill the dialog when creating a new feature. Selections are not remembered.
    #: Only kept in memory, so this resets when the add-in is reloaded.
    _last_used_settings: dict[str, typing.Any] = dataclasses.field(default_factory=dict, init=False)

    def __post_init__(self):

        repeated = [p for p in self.parameters if isinstance(p, SelectionParameterDefinition) and p.repeat]
        assert len(repeated) <= 1, "At most one selection parameter can have repeat=True"

        # Command definition for the feature creation command
        create_command_definition_id = self.id + '_create'
        utils.delete_from_collection(ui.commandDefinitions, create_command_definition_id)
        self._create_command_definition = ui.commandDefinitions.addButtonDefinition(create_command_definition_id, self.name, self.tooltip, self.icon_path)
        self._permanent_handlers.append(register_event_handler(self._create_command_definition.commandCreated, self._on_create_command_created))

        # Command definition for the feature edit command
        edit_command_definition_id = self.id + '_edit'
        utils.delete_from_collection(ui.commandDefinitions, edit_command_definition_id)
        self._edit_command_definition = ui.commandDefinitions.addButtonDefinition(edit_command_definition_id, self.name, self.tooltip, self.icon_path)
        self._permanent_handlers.append(register_event_handler(self._edit_command_definition.commandCreated, self._on_edit_command_created))

        # Custom feature definition
        self._custom_feature_definition = adsk.fusion.CustomFeatureDefinition.create(self.id, self.name, self.icon_path)
        self._custom_feature_definition.editCommandId = self._edit_command_definition.id
        self._permanent_handlers.append(register_event_handler(self._custom_feature_definition.customFeatureCompute, self._on_feature_recompute))
        
    def validate_parameters(self, params: dict[str, typing.Any]) -> bool:
        """
        Checks if the given parameters are valid.
        This controls if the 'OK' button is grayed out.

        WARNING: This is invoked during previews. The selected elements might not be valid 
        because the modifications of this feature has been applied.
        
        The parameter dict uses the id of the input field as the key. 
        The value is the value of the input field in database units (cm for lengths).
        If the input field is a selection, then the value is a list of objects. 
        """
        raise NotImplementedError("abstract")
    
    def identify_target_body(self, params: dict[str, typing.Any]) -> adsk.fusion.BRepBody:
        """
        The feature is applied to this pre-existing target body.

        The parameter dict uses the id of the input field as the key. 
        The value is the value of the input field in database units (cm for lengths).
        If the input field is a selection, then the value is a list of objects. 
        """

    def generate_tool_body(self, params: dict[str, typing.Any]) -> adsk.fusion.BRepBody:
        """
        Creates the tool body that is combined with the target body through a boolean operation.

        The parameter dict uses the id of the input field as the key. 
        The value is the value of the input field in database units (cm for lengths).
        If the input field is a selection, then the value is a list of objects. 
        """
        raise NotImplementedError("abstract")

    def add_to_toolbar(self, workspace_id, panel_id, promote=True):
        """
        Adds the feature icon to the toolbar.
        """
        workspace = ui.workspaces.itemById(workspace_id)
        panel = workspace.toolbarPanels.itemById(panel_id)

        utils.delete_from_collection(panel.controls, self._create_command_definition.id)
        self._toolbar_control = panel.controls.addCommand(self._create_command_definition)
        self._toolbar_control.isPromoted = promote

    ##################
    # Internal helpers
    ##################

    def _input_values_to_dict(self, inputs: adsk.core.CommandInputs) -> dict[str, typing.Any]:
        """
        Extacts the current values of all the inputs and puts them into a dict.
        """
        values = {}
        for param in self.parameters:
            ci = self._current_command.commandInputs.itemById(param.id)
            values[param.id] = param.value(ci)
        return values

    @property
    def _repeated_parameter(self) -> typing.Optional[SelectionParameterDefinition]:
        """
        The selection parameter with repeat=True, or None.
        """
        for param in self.parameters:
            if isinstance(param, SelectionParameterDefinition) and param.repeat:
                return param
        return None

    def _split_params(self, params: dict[str, typing.Any]) -> list[dict[str, typing.Any]]:
        """
        Splits the parameters into one set per feature instance to be created.
        Without a repeated parameter, this is just the given parameters.
        With a repeated parameter, there is one set per selected entity (empty if nothing is selected).
        """
        repeated = self._repeated_parameter
        if repeated is None:
            return [params]
        return [{**params, repeated.id: [entity]} for entity in params[repeated.id]]

    def _validate_all(self, params: dict[str, typing.Any]) -> bool:
        """
        Validates the parameters of every feature instance that would be created.
        """
        parts = self._split_params(params)
        return bool(parts) and all(self.validate_parameters(p) for p in parts)

    @staticmethod
    def _refind_entity(entity: adsk.core.Base, token: str) -> typing.Optional[adsk.core.Base]:
        """
        Returns the current version of an entity after previous operations may have modified it.
        Returns None if it can't be identified unambiguously (e.g. it has been split or consumed).
        """
        if entity is not None and entity.isValid:
            return entity
        design: adsk.fusion.Design = app.activeProduct
        candidates = [e for e in design.findEntityByToken(token) if e is not None and e.isValid]
        if len(candidates) != 1:
            return None
        return candidates[0]

    def _group_in_timeline(self, features: list[adsk.fusion.CustomFeature]):
        """
        Puts the given features, which must be adjacent in the timeline, into a timeline group.
        Grouping is cosmetic, so failures are only logged.
        """
        if len(features) < 2:
            return
        try:
            design: adsk.fusion.Design = app.activeProduct
            start = features[0].timelineObject.index
            end = features[-1].timelineObject.index
            group = design.timeline.timelineGroups.add(start, end)
            group.name = f"{self.name} ×{len(features)}"
        except Exception:
            logger.warning("Unable to group the created features in the timeline", exc_info=True)

    def _remember_settings(self, inputs: adsk.core.CommandInputs):
        """
        Stores the current settings of the dialog so that the next create dialog starts with them.
        Selections are skipped, they are specific to each application of the feature.
        """
        for param in self.parameters:
            if param.expression_type == ExpressionType.Entity:
                continue
            ci = inputs.itemById(param.id)
            self._last_used_settings[param.id] = param.remember(ci)

    def _feature_to_dict(self, feature: adsk.fusion.CustomFeature) -> dict[str, typing.Any]:

        params = {}
        for param in self.parameters:
            match param.expression_type:
                case ExpressionType.Number:
                    value = feature.parameters.itemById(param.id).value
                    value = param.value_type(value)
                case ExpressionType.String:
                    if param.value_type == str:
                        value = feature.parameters.itemById(param.id).textValue
                    else:
                        value = feature.parameters.itemById(param.id).value
                        value = param.value_type(value)
                case ExpressionType.Entity:
                    param: SelectionParameterDefinition = param
                    value = param.from_dependencies(feature.dependencies)
            params[param.id] = value

        return params

    def _add_custom_feature_dependencies_from_command_inputs(self, feature: adsk.fusion.CustomFeature, inputs: adsk.core.CommandInputs, params: dict[str, typing.Any]):
        """
        Adds dependencies to the custom feature for all selection inputs.
        """

        # Remember the current position of the timeline
        design: adsk.fusion.Design = app.activeProduct
        timeline = design.timeline
        marker_position = timeline.markerPosition
        original_timeline_position = timeline.item(marker_position - 1)

        # Rollback the timeline to before this feature
        feature.timelineObject.rollTo(rollBefore=True)

        for param in self.parameters:
            if param.expression_type != ExpressionType.Entity:
                continue
            param: SelectionParameterDefinition = param
            for dep_id, entity in param.as_dependencies(params[param.id]):
                dep = feature.dependencies.itemById(dep_id)
                if dep:
                    dep.entity = entity
                else:
                    feature.dependencies.add(dep_id, entity)

        # Restore timeline marker
        original_timeline_position.rollTo(rollBefore=False)

    def _apply_feature(self, params: dict[str, typing.Any], is_preview: bool):
        """
        Creates the feature instance(s) for the dialog's parameters. On its own, this modifies the timeline.

        With a repeated selection parameter, one instance is created per selected entity, in selection order.
        This is equivalent to applying the feature once per entity: each instance is computed from the
        geometry at its own position in the timeline, i.e. after the previous instances have been applied.
        """
        if not self._validate_all(params):
            logger.info(f"Unable to apply. Invalid parameters.")
            return

        repeated = self._repeated_parameter
        if repeated is None:
            self._apply_single_feature(params)
            return

        entities = params[repeated.id]

        # Capture tokens before modifying anything. The entity objects may become invalid once
        # a previous instance modifies their body, the tokens let us find them again.
        tokens = [entity.entityToken for entity in entities]

        features = []
        skipped = []
        for index, (entity, token) in enumerate(zip(entities, tokens)):
            entity = self._refind_entity(entity, token)
            feature = None
            if entity is not None:
                feature = self._apply_single_feature({**params, repeated.id: [entity]})
            if feature is None:
                logger.warning(f"Skipped selection #{index + 1}: it was changed by an earlier instance in this selection and is no longer valid.")
                skipped.append(index + 1)
            else:
                features.append(feature)

        if is_preview:
            return

        self._group_in_timeline(features)

        if skipped:
            ui.messageBox(
                f"{len(skipped)} of the {len(entities)} selected {repeated.name.lower()} could not be processed "
                f"because the {self.name} features created before them changed them (selection #{', #'.join(map(str, skipped))}).\n\n"
                f"Try a different selection order, or apply {self.name} to those separately.",
                self.name,
                adsk.core.MessageBoxButtonTypes.OKButtonType,
                adsk.core.MessageBoxIconTypes.WarningIconType)

    def _apply_single_feature(self, params: dict[str, typing.Any]) -> typing.Optional[adsk.fusion.CustomFeature]:
        """
        Creates one feature instance. On its own, this modifies the timeline.
        Returns the created feature, or None if the parameters are invalid.
        """

        if not self.validate_parameters(params):
            logger.info(f"Unable to apply. Invalid parameters.")
            return None

        target_body = self.identify_target_body(params)
        tool_body = self.generate_tool_body(params)
        component = target_body.parentComponent

        # Put the body into a base feature to convert it to a body that is persisted in the history
        base_feature = component.features.baseFeatures.add()
        base_feature.startEdit()
        component.bRepBodies.add(tool_body, base_feature)
        base_feature.finishEdit()

        # Create the boolean operation
        tool_body_collection = adsk.core.ObjectCollection.create()
        tool_body_collection.add(base_feature.bodies.item(0))
        boolean_operation = component.features.combineFeatures.createInput(target_body, tool_body_collection)
        boolean_operation.operation = self.boolean_operation
        combine_feature = component.features.combineFeatures.add(boolean_operation)

        # Create the parameters stored in the custom feature instance.
        # We'll need them to recompute and edit.
        custom_feature_inputs = component.features.customFeatures.createInput(self._custom_feature_definition)
        for param in self.parameters:
            ci = self._current_command.commandInputs.itemById(param.id)
            match param.expression_type:
                case ExpressionType.Number:
                    value_input = adsk.core.ValueInput.createByReal(param.expression(ci))
                case ExpressionType.String:
                    value_input = adsk.core.ValueInput.createByString(param.expression(ci))
                case ExpressionType.Entity:
                    continue  # Dependencies are handled separately
            custom_feature_inputs.addCustomParameter(param.id, label=param.id, units=param.unit, value=value_input)

        # Group the operations we previously performed into the custom feature
        assert custom_feature_inputs.setStartAndEndFeatures(base_feature, combine_feature)

        # Create the custom feature instance by adding the inputs.
        feature = component.features.customFeatures.add(custom_feature_inputs)

        # Add dependencies to the selected entities
        self._add_custom_feature_dependencies_from_command_inputs(feature, self._current_command.commandInputs, params)

        return feature

    def _edit_feature(self, params: dict[str, typing.Any], is_preview: bool):
        feature = self._currently_edited_feature
        assert feature is not None

        for param in self.parameters:
            ci = self._current_command.commandInputs.itemById(param.id)
            match param.expression_type:
                case ExpressionType.Number:
                    feature.parameters.itemById(param.id).value = param.value(ci)
                case ExpressionType.String:
                    feature.parameters.itemById(param.id).expression = param.expression(ci)
                case ExpressionType.Entity:
                    continue  # Dependencies are handled separately

        # self._set_custom_feature_params(self._current_command.commandInputs, feature)
        self._add_custom_feature_dependencies_from_command_inputs(feature, self._current_command.commandInputs, params)

        tool_body = self.generate_tool_body(params)

        # Find the base feature within our custom feature
        base_feature = [f for f in feature.features if isinstance(f, adsk.fusion.BaseFeature)][0]
        base_feature.startEdit()

        # Replace the body inside the base feature with the new tool
        body: adsk.fusion.BRepBody = base_feature.bodies.item(0)
        base_feature.updateBody(body, tool_body)
        base_feature.finishEdit()

    def _recompute_feature(self, feature: adsk.fusion.CustomFeature) -> bool:
        """
        Regenerates the tool body of an existing feature instance.
        Returns False if the feature can't be computed. The previous tool body is kept in that case.
        """
        params = self._feature_to_dict(feature)

        # Check for lost references before validating. validate_parameters() may deliberately accept
        # None entities (they occur during previews), but here they mean the entity is gone.
        for param in self.parameters:
            if param.expression_type != ExpressionType.Entity:
                continue
            entities = params[param.id]
            if len(entities) < param.min_count or any(e is None or not e.isValid for e in entities):
                logger.warning(f"{self.name} '{feature.name}': '{param.name}' references something that no longer exists. Edit the feature to select a replacement.")
                return False

        if not self.validate_parameters(params):
            logger.warning(f"{self.name} '{feature.name}': the parameters or selections are no longer valid. Edit the feature to fix them.")
            return False

        tool_body = self.generate_tool_body(params)

        # Find the base feature within our custom feature
        base_feature = [f for f in feature.features if isinstance(f, adsk.fusion.BaseFeature)][0]
        base_feature.startEdit()

        # Replace the body inside the base feature with the new tool
        body: adsk.fusion.BRepBody = base_feature.bodies.item(0)
        base_feature.updateBody(body, tool_body)
        base_feature.finishEdit()
        return True

    ################
    # Event Handlers
    ################

    def _on_create_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Invoked when a new instance of this feature is created. A command has been created.
        """
        logger.info("_on_create_command_created()")
        self._status = self._Status.Creating
        self._on_command_created(args)


    def _on_edit_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Invoked when an existing instance of this feature is edited. A command has been created.
        """
        logger.info("_on_edit_command_created()")
        self._status = self._Status.Editing
        self._on_command_created(args)

    def _on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Invoked when a create or edit command is created.
        This callback is invoked from either _on_create_command_created() or _on_edit_command_created()
        self._status has already been updated, which allows differentiation.
        """
        self._current_command = args.command

        # Create command inputs with initial values
        for param in self.parameters:
            ci = param.create_and_add_command_input(self._current_command.commandInputs)
            
        if self._status == self._Status.Creating:
            # Set the input fields to the last used settings, or their initial values
            for param in self.parameters:
                ci = self._current_command.commandInputs.itemById(param.id)
                if param.id in self._last_used_settings:
                    param.restore(ci, self._last_used_settings[param.id])
                else:
                    param.update_command_input_from_expression(ci, param.inital_expression)

        elif self._status == self._Status.Editing:
            
            # Find the feature we're editing
            assert ui.activeSelections.count == 1
            custom_feature = ui.activeSelections.item(0).entity
            assert custom_feature is not None
            assert isinstance(custom_feature, adsk.fusion.CustomFeature)
            self._currently_edited_feature = custom_feature

            # Each instance depends on exactly one entity of the repeated parameter
            repeated = self._repeated_parameter
            if repeated is not None:
                ci: adsk.core.SelectionCommandInput = self._current_command.commandInputs.itemById(repeated.id)
                ci.setSelectionLimits(1, 1)

            # Set the input fields to the parameters stored in the feature.
            # The select inputs are not yet set.
            for param in self.parameters:
                match param.expression_type:
                    case ExpressionType.Entity:
                        continue
                    case ExpressionType.String:
                        expression = custom_feature.parameters.itemById(param.id).expression
                    case ExpressionType.Number:
                        expression = custom_feature.parameters.itemById(param.id).value
                    case _:
                        raise RuntimeError(f"Invalid expression type {param.expression_type} of {param.id}")
                ci = self._current_command.commandInputs.itemById(param.id)
                param.update_command_input_from_expression(ci, expression)
        else:
            raise RuntimeError(f"Invalid status {self._status}")


        self._current_command_handlers = []
        self._current_command_handlers.append(register_event_handler(self._current_command.destroy, self._on_command_destroy))
        self._current_command_handlers.append(register_event_handler(self._current_command.validateInputs, self._on_validate_inputs))
        self._current_command_handlers.append(register_event_handler(self._current_command.preSelect, self._on_pre_select))
        self._current_command_handlers.append(register_event_handler(self._current_command.executePreview, self._on_preview))
        self._current_command_handlers.append(register_event_handler(self._current_command.execute, self._on_execute))

        if self._status == self._Status.Editing:
            self._current_command_handlers.append(register_event_handler(self._current_command.activate, self._on_activate))

    def _on_command_destroy(self, args: adsk.core.CommandEventArgs):
        """
        Invoked when the current command ends.
        """
        logger.info("_on_command_destroy()")

        if self._original_timeline_position is not None:
            self._original_timeline_position.rollTo(rollBefore=False)
            self._original_timeline_position = None

        self._status = self._Status.Inactive
        self._current_command_handlers = []
        self._current_command = None
        self._currently_edited_feature = None

    def _on_activate(self, args: adsk.core.CommandEventArgs):
        """
        Invoked when the edit command is activated.
        """
        logger.info("_on_activate()")
        design: adsk.fusion.Design = app.activeProduct

        # Remember the current position of the timeline.
        timeline = design.timeline
        marker_position = timeline.markerPosition
        self._original_timeline_position = timeline.item(marker_position - 1)

        # Rollback the timeline to the point in time the custom feature was created.
        self._currently_edited_feature.timelineObject.rollTo(True)

        # Don't understand why this is needed
        args.command.beginStep()

        # Since we rolled back on the timeline, we can now update the selection inputs.
        for param in self.parameters:
            if param.expression_type != ExpressionType.Entity:
                continue
            param: SelectionParameterDefinition = param
            expression = param.from_dependencies(self._currently_edited_feature.dependencies)
            ci = self._current_command.commandInputs.itemById(param.id)
            param.update_command_input_from_expression(ci, expression)

        logger.info("_on_activate() done")

    def _on_validate_inputs(self, args: adsk.core.ValidateInputsEventArgs):
        """
        Invoked to decide if the dialog's "OK" button should be active.
        Only invoked when there is an active command (create or edit).
        """
        logger.info("_on_validate_inputs()")
        params = self._input_values_to_dict(args.inputs)
        args.areInputsValid = self._validate_all(params)

    def _on_pre_select(self, args: adsk.core.SelectionEventArgs):
        logger.info("_on_pre_select()")

        # Collect all other parameters
        params = self._input_values_to_dict(args.activeInput.commandInputs)

        # Overwrite the parameter for the active input with that of the pre selection
        params[args.activeInput.id] = [args.selection.entity]

        # It's selectable if this results in a valid set of parameters
        args.isSelectable = self.validate_parameters(params)

    def _on_preview(self, args: adsk.core.CommandEventArgs):
        """
        Invoked the generate the preview
        """
        logger.info("_on_preview()")
        params = self._input_values_to_dict(args.command.commandInputs)

        # Apply the feature. Fusion will take care of undoing the changes.
        self._apply_feature(params, is_preview=True)

    def _on_execute(self, args: adsk.core.CommandEventArgs):
        """
        Invoked when the 'OK' button is pressed. 
        """
        logger.info("_on_execute()")
        params = self._input_values_to_dict(args.command.commandInputs)
        self._remember_settings(args.command.commandInputs)
        if self._status == self._Status.Creating:
            self._apply_feature(params, is_preview=False)
        elif self._status == self._Status.Editing:
            self._edit_feature(params, is_preview=False)

    def _on_feature_recompute(self, args: adsk.fusion.CustomFeatureEventArgs):
        logger.info("_on_feature_recompute()")
        if self._current_command is not None:
            logger.info("ignoring recompute while command is active")
            return
        feature = args.customFeature
        try:
            success = self._recompute_feature(feature)
        except Exception:
            logger.exception(f"{self.name} '{feature.name}': recompute failed")
            success = False
        if not success:
            # Marks the feature red in the timeline. Only predefined message ids are supported,
            # the details are in the log.
            args.computeStatus.statusMessages.addError('DRPOINT_COMPUTE_FAILED', '')

    def __del__(self):
        #: Unregister all handlers
        self._permanent_handlers = []
        #: Destroy all objects
        utils.delete_if_exists(self._toolbar_control)
        utils.delete_if_exists(self._edit_command_definition)
        utils.delete_if_exists(self._create_command_definition)
        
        

