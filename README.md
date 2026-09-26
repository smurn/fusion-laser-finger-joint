# Laser Finger Joint

A Fusion add-in for designing laser-cut parts with finger joints. It adds a **Laser Finger Joint** command to *Solid → Modify*: select the edge face of a flat part and it cuts a finger pattern into it, as a parametric feature that stays in the timeline and can be edited later.

## Features

- **Parametric.** Each joint is a custom feature in the timeline. It recomputes when upstream geometry changes and can be edited like a built-in feature.
- **Multiple faces at once.** Select several faces and one joint is created per face, in selection order, grouped in the timeline.
- **Automatic finger count.** The number of fingers is chosen so their width comes as close as possible to your preferred width, within the min/max limits.
- **Expressions.** Lengths accept expressions and user parameters, e.g. `ply` or `ply * 2`.
- **Remembers settings.** The dialog starts with the settings you last confirmed (for the current Fusion session).
- **Clear errors.** If an upstream change breaks a joint, the feature turns red in the timeline and the reason is written to the text console. Edit it and pick a new face to repair it.

## Installation

Fusion's add-in folder is:
- Windows: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns`
- macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns`

1. Either download `LaserFingerJoint-<version>.zip` from the [latest release](https://github.com/smurn/fusion-laser-finger-joint/releases/latest) and unzip it into the add-in folder, or clone the repository there:

   ```
   git clone https://github.com/smurn/fusion-laser-finger-joint.git "Laser Finger Joint"
   ```

   The folder must be named `Laser Finger Joint`, to match `Laser Finger Joint.py` and `Laser Finger Joint.manifest`.

2. In Fusion, open *Scripts and Add-Ins* (Shift+S), select **Laser Finger Joint** under *Add-Ins* and click **Run**.

See [docs/help.html](docs/help.html) for the user guide.

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

- `Laser Finger Joint.py`: add-in entry point.
- `laser_finger_joint_feature.py`: the Laser Finger Joint feature: parameters, face validation and the geometry of the cutouts.
- `sane/`: a small framework on top of Fusion's custom feature API. A feature declares its parameters and implements validation and tool-body generation. The framework handles the dialog, creating/editing/recomputing the feature, multi-selection (one feature per selected entity), remembering settings and error reporting.

Requires the Python bundled with current Fusion versions (3.12 or newer).

## Building and releasing

`python tools/build.py` builds `dist/LaserFingerJoint-<version>.zip` (the add-in folder, for manual installation) and `dist/LaserFingerJoint-<version>.bundle.zip` (the Autodesk App Store bundle). The version comes from the manifest. Pushing a tag `v<version>` creates a GitHub release with both files. See [docs/store/SUBMISSION.md](docs/store/SUBMISSION.md) for the App Store submission.

## Privacy

The add-in collects no data and makes no network connections. See [PRIVACY.md](PRIVACY.md).

## License

MIT, see [LICENSE](LICENSE).
