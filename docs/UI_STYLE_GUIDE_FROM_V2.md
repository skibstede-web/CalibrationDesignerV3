# UI Style Guide Extracted From CalibrationDesignerV2

This document captures the UI/UX style currently implemented in CalibrationDesignerV2 and maps it for later application to CalibrationDesignerV3.

## 1. V2 UI framework/library used
- Primary desktop UI library: `customtkinter` (CTk widgets)
- Base toolkit beneath CTk: Tkinter
- Table rendering: `ttk.Treeview` inside custom frames for dataframe-like output tabs
- Plot preview loading in UI: `tkinter.PhotoImage` wrapped for CTk preview label
- Image loading for header logo: `PIL.Image` (Pillow) + `ctk.CTkImage`

## 2. Main layout pattern
- Window: large desktop canvas (`1500x920`), minimum size constrained (`1200x750`)
- Overall structure:
  - Top branded header bar
  - Main scrollable content area
  - Sticky bottom action row (always visible)
- Main content segmentation:
  - Primary row: two side-by-side panels
    - left: "Design Input"
    - right: "Components Input"
  - Secondary row: collapsible "Advanced Settings" container with segmented switch:
    - "Stock & Volumes"
    - "Pipette Inventory"
  - Output row: tabbed results area
- Layout behavior is grid/pack hybrid, with explicit row/column weights for resizing.

## 3. Color palette with hex codes
Extracted from `COLORS` constant in V2 `main_window.py`:
- Primary: `#12355B` (deep blue)
- Accent: `#F28C28` (orange)
- Background: `#FAF7F2` (warm off-white)
- Panel: `#FFFFFF` (white)
- Secondary panel: `#EEF3F7` (pale blue-gray)
- Text: `#0B1F33` (dark blue-black)
- Secondary text: `#5F6C7B` (muted slate)
- Border: `#D8E0E8` (light cool gray)

Additional status tones in output/validation:
- Pass: `#2E7D32`
- Warning: `#F9A825`
- Fail/Critical: `#C62828`
- Info: `#1976D2`
- Validation warning background: `#FFF4DD`
- Validation error background: `#FDE7E7`

## 4. Typography/font observations
- Default font stack comes from CTk/Tk; no custom font family override is set.
- Hierarchy via size/weight:
  - App title: ~24 bold
  - Panel titles: ~18 bold
  - Sub-panel headers: ~15 bold
  - Body labels/default text: standard CTk size
- Heavy use of clear sentence-case labels and helper descriptions.
- Secondary/helper copy rendered in muted secondary text color.

## 5. Button styling
- Primary action emphasis:
  - "Run Design Optimizer" uses accent orange fill with bold dark text.
  - Larger size (`height` ~40, wider width).
- Secondary actions:
  - Deep-blue fill, white text, darker blue hover.
- Advanced section toggle:
  - Blue button with explicit Show/Hide state text.
- Segmented control:
  - Selected segment in primary blue, selected hover in accent.

## 6. Panel/card styling
- Panels are card-like CTk frames:
  - rounded corners (`corner_radius` ~10)
  - bordered (light gray border)
  - white or secondary-panel background
- Top header card:
  - primary blue background
  - accent border
  - white title text + orange subtitle
- Secondary/advanced area:
  - nested card pattern (secondary panel outer, white panel inner)
- Visual hierarchy is driven by background contrast + border.

## 7. Input section styling
- Input labels on left, controls on right (forms) or in table/grid layout.
- "Design Input" is compact form-based.
- "Components Input" is a scrollable table-style editor with bold header row.
- Section descriptions explain intent and constraints.
- Real-time validation pattern:
  - change listeners (`trace_add`) on all key fields
  - run button enabled/disabled by validation state
  - visible validation banner in sticky action row for issues/guidance

## 8. Output section styling
- Output presented as a multi-tab workspace.
- Data tabs use tree tables with:
  - auto-sized column widths
  - horizontal + vertical scrollbars
  - severity row highlighting (`critical`, `warning`, `info`)
- Summary tab has status badge color chip and textual run summary.
- Files tab provides artifact list + open actions.

## 9. Plot/tab styling
- Plots tab in V2 is list-and-preview:
  - listbox of plot filenames
  - preview area below
  - fallback message if preview unavailable
  - "Open Selected Plot" action
- Plot artifacts are filesystem-first: UI is a preview/browser over generated files.
- Plot preview is intentionally basic and reliable file-open remains a core flow.

## 10. Sticky bottom action bar implementation notes
- Implemented as a dedicated bottom row frame outside scroll area.
- Always visible while content scrolls above it.
- Contains:
  - primary run action
  - utility actions (open folder, save/load config)
  - dynamic status text
  - validation banner region
- Banner behavior:
  - hidden when clean
  - warning or error background/colors based on validation severity
  - wrap length updated on resize.

## 11. Logo file path copied into V3
- V2 source logo path:
  - `C:\Users\Erik\Documents\Projects\CalibrationDesignerV2\src\calibration_designer\assets\logo.png`
- Copied to V3 destination:
  - `C:\Users\Erik\Documents\Projects\CalibrationDesignerV3\src\calibration_designer_v3\assets\logo.png`

## 12. Specific recommendations for applying the V2 style to CalibrationDesignerV3
- Adopt the same palette constants and use them consistently across:
  - root background
  - cards/panels
  - section headers
  - buttons and hover states
  - status and validation banners
- Move V3 to `customtkinter` for parity (V3 currently uses Tk widgets).
- Mirror the three-tier layout:
  - branded top header
  - scrollable body with primary + secondary + outputs blocks
  - sticky action bar with validation state
- Preserve V3 functionality but wrap each major area in rounded bordered cards.
- Convert output area to tabbed CTk frame model with:
  - summary status badge
  - table tabs with severity highlighting
  - plots browser tab (file list + preview)
- Keep advanced settings collapsible/segmented to reduce visual load.
- Keep helper text under key sections to preserve scientific usability.
- Maintain deterministic status messaging in the action row.

## 13. Files in V3 that likely need to be changed later
Likely primary targets for visual restyle implementation:
- `src/calibration_designer_v3/ui/main_window.py`
- `src/calibration_designer_v3/ui/input_state.py` (if UI model/view binding needs style-driven refactor)
- `src/calibration_designer_v3/plotting/plots.py` (only if plot presentation defaults are aligned to V2 conventions)
- `src/calibration_designer_v3/app.py` (if initialization/bootstrap changes for CTk)

Potential additions:
- `src/calibration_designer_v3/ui/output_tabs.py` (if splitting output tab logic like V2)
- centralized style module (recommended), e.g.:
  - `src/calibration_designer_v3/ui/style.py`

## V2 files inspected
- `src/calibration_designer/ui/main_window.py`
- `src/calibration_designer/ui/output_tabs.py`
- `src/calibration_designer/ui/components_panel.py`
- `src/calibration_designer/ui/design_panel.py`
- `src/calibration_designer/ui/stock_volumes_panel.py`
- `README.md`
- asset folder: `src/calibration_designer/assets/`
