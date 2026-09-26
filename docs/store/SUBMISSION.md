# Autodesk App Store submission

Everything needed to list Laser Finger Joint on the Autodesk App Store (now the *Autodesk Design and Make Marketplace*).

- Publisher Center: https://aps.autodesk.com/app-store/publisher-center
- Upload portal: https://apps.autodesk.com/en/MyUploads
- Fusion publishing guidelines: https://aps.autodesk.com/app-store/publisher-center/fusion-360
- Marketing and technical information form: https://www.autodesk.com/content/dam/autodesk/www/adn/pdf/app-submission-marketing-technical-information.doc
- Icon guidelines: https://www.autodesk.com/content/dam/autodesk/www/adn/pdf/icon-publishers.zip
- Questions: appsubmissions@autodesk.com

## Package

Build with `python tools/build.py`, or download from the GitHub release (see *Releasing* below). Submit `dist/LaserFingerJoint-<version>.bundle.zip`. It contains `Laser Finger Joint.bundle`:

```
Laser Finger Joint.bundle/
    PackageContents.xml      generated from the manifest by tools/build.py
    Contents/
        Laser Finger Joint.manifest
        Laser Finger Joint.py
        laser_finger_joint_feature.py, sane/, resources/, ...
        Help.html            from docs/help.html
        LICENSE
```

Autodesk builds the installer from the bundle. `PackageContents.xml` uses a fixed `UpgradeCode` for all versions and a `ProductCode` derived from the version, so every version has its own code.

## Before submitting

- [ ] **Test the bundle on Windows.** Stop the development copy (Scripts and Add-Ins → Stop, and untick *Run on Startup*), because both register the same command. Unzip the bundle into `%APPDATA%\Autodesk\ApplicationPlugins`, restart Fusion and check that the command appears under Solid → Modify, creates, edits and recomputes joints. Remove the test bundle afterwards.
- [ ] **Test the bundle on macOS**, same steps, in `~/Library/Application Support/Autodesk/ApplicationPlugins`.
- [ ] **Screenshots** (see below).
- [ ] **Optional: short video** (30–60 s) showing a joint being created on two faces and then edited.
- [ ] **Publisher account** created in the Publisher Center.

## Listing

**Title:** Laser Finger Joint

**Price:** Free

**Operating systems:** Windows, macOS

**Language:** English

**Category:** Modeling / design tools *(choose the closest in the portal)*

**Short description** (one sentence):

> Parametric finger joints for laser-cut parts: select the edges of flat parts and cut a finger pattern that stays editable in the timeline.

**Description:**

> Laser Finger Joint adds finger joints for laser cutting to Fusion. Select the edge face of a flat part, set the finger depth and preferred width, and the add-in cuts an evenly spaced finger pattern into it.
>
> The joint is a real parametric feature in the timeline. When the part changes, the joint updates. You can edit it at any time, just like Fusion's built-in features.
>
> Features:
> - Parametric: joints recompute when upstream geometry changes and can be edited later.
> - Select several edges at once; one joint is created per edge and grouped in the timeline.
> - Make the mating part with a standard Combine → Cut using the jointed part as the tool, so both parts always match exactly.
> - The number of fingers is chosen automatically to match your preferred finger width, within the limits you set.
> - Choose whether each end starts with a finger or a cutout, and leave an uncut margin at either end.
> - Use expressions and user parameters, e.g. a `ply` parameter for your material thickness, so changing the material updates every joint.
> - Clear error reporting: if a change breaks a joint, it is marked in the timeline and can be repaired by re-selecting the face.
>
> Open source under the MIT license: https://github.com/smurn/fusion-laser-finger-joint

**Keywords:** laser cutting, finger joint, box joint, laser cutter, plywood, acrylic, CNC, joinery, sheet parts, parametric

**Support:** https://github.com/smurn/fusion-laser-finger-joint/issues

**Privacy policy:** https://github.com/smurn/fusion-laser-finger-joint/blob/main/PRIVACY.md

**Help:** bundled as `Help.html`. The portal's documentation form can reuse the text of `docs/help.html`.

**Release notes 1.0.0:** First release.

## Screenshots

Take them at a decent resolution with a clean model (e.g. a simple open box from 3–5 mm panels):

1. The dialog open with the preview showing fingers on an edge.
2. A finished box whose panels are joined with finger joints.
3. The timeline with a group of joints, and the right-click *Edit Feature* on one of them.
4. Several edges selected at once, with the preview on all of them.

## Releasing a new version

1. Set the new version in `Laser Finger Joint.manifest` (`"version"`).
2. Commit, then tag and push: `git tag v1.0.1 && git push origin main v1.0.1`.
3. The *Build* workflow creates a GitHub release with `LaserFingerJoint-<version>.bundle.zip` (for the store) and `LaserFingerJoint-<version>.zip` (for manual installation).
4. Upload the bundle zip as a new version in the store portal. Each store update needs a new version number.
