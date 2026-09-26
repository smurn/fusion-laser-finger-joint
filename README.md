# Laser Joint

A Fusion add-in for designing laser-cut parts with finger joints. It adds a **Laser Finger** command to *Solid → Modify*: select the edge face of a flat part and it cuts a finger pattern into it, as a parametric feature that stays in the timeline and can be edited later.

## Features

- **Parametric.** Each joint is a custom feature in the timeline. It recomputes when upstream geometry changes and can be edited like a built-in feature.
- **Multiple faces at once.** Select several faces and one joint is created per face, in selection order, grouped in the timeline.
- **Automatic finger count.** The number of fingers is chosen so their width comes as close as possible to your preferred width, within the min/max limits.
- **Expressions.** Lengths accept expressions and user parameters, e.g. `ply` or `ply * 2`.
- **Remembers settings.** The dialog starts with the settings you last confirmed (for the current Fusion session).
- **Clear errors.** If an upstream change breaks a joint, the feature turns red in the timeline and the reason is written to the text console. Edit it and pick a new face to repair it.

## Installation

The add-in folder must be named `Laser Joint`, to match `Laser Joint.py` and `Laser Joint.manifest`.

1. Clone the repository into Fusion's add-in folder:
   - Windows: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns`
   - macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns`

   ```
   git clone https://github.com/smurn/fusion-laser-joint.git "Laser Joint"
   ```

2. In Fusion, open *Scripts and Add-Ins* (Shift+S), select **Laser Joint** under *Add-Ins* and click **Run**.

## Usage

Select one or more faces and set the parameters:

| Parameter | Meaning |
|---|---|
| Faces | Faces the fingers are cut into. Each must be flat and rectangular (four straight, perpendicular edges, no holes). The pattern runs along the face's longest edge. |
| Finger depth | How deep the cutouts go, usually the material thickness of the mating part. |
| Preferred width | The finger width to aim for. |
| Min. / Max. finger count | Limits on the number of fingers. |
| Begin / End with finger | Whether the pattern starts/ends with a finger (material left standing) or a cutout. |
| Offset at the beginning / end | Length at each end of the edge that is left uncut. |

Fingers and gaps have the same width. If no finger count satisfies the settings (e.g. the offsets are longer than the edge), the face is rejected.

## Code structure

- `Laser Joint.py`: add-in entry point.
- `laser_finger_feature.py`: the Laser Finger feature: parameters, face validation and the geometry of the cutouts.
- `sane/`: a small framework on top of Fusion's custom feature API. A feature declares its parameters and implements validation and tool-body generation. The framework handles the dialog, creating/editing/recomputing the feature, multi-selection (one feature per selected entity), remembering settings and error reporting.

Requires the Python bundled with current Fusion versions (3.12 or newer).

## License

MIT, see [LICENSE](LICENSE).
