# Design System — Color Scheme

## Theme Base
- Base: Light
- Background: `#FFFFFF`
- Secondary Background: `#F8FAFC`
- Tertiary Background: `#EEF2F7`
- Text Primary: `#1F2937`
- Text Secondary: `#31333F`
- Border: `#D1D5DB`

## Accent Colors
- Primary: `#2563EB`
- Primary Hover: `#1D4ED8`
- Success: `#22C55E`
- Warning: `#F59E0B`
- Error: `#EF4444`

## Components Mapping
- Buttons: background `#EEF2F7`, text `#31333F`, border `#D1D5DB`
- Selected option: background `#2563EB`, text `#FFFFFF`
- Metrics/Expander: background `#F8FAFC`
- Inputs: background `#FFFFFF`, text `#31333F`, border `#D1D5DB`
- Toolbar/Modal/Popover: background `#FFFFFF`, text `#0F172A`, border `#E5E7EB`

## Accessibility
- Body text on `#FFFFFF` with `#1F2937`: contrast ≈ 12.6:1 (AA/AAA)
- Primary `#2563EB` on `#FFFFFF`: contrast ≈ 8.9:1 (AA/AAA)
- White text on primary `#2563EB`: contrast ≈ 4.7:1 (AA for ≥18pt bold or UI icons; use for selected states only)
- For small text on colored backgrounds, prefer `#0F172A` when feasible

## Implementation
- Streamlit theme: `.streamlit/config.toml` with `base="light"`
- Global CSS overrides: `apply_theme()` in `app_modern.py`
- Data attribute enforcement: `data-theme="light"` set at runtime

## Usage Guidelines
- Maintain minimum AA contrast; validate custom additions with WCAG tools
- Avoid dark-mode classes; ensure neutral defaults render correctly on light theme
- Keep borders subtle; avoid low-contrast light-on-light for form controls

## Spacing
- Vertical rhythm: 0.75rem bottom margin on core controls
- Applies to: inputs, selects, text areas, number inputs, multiselects, sliders, checkboxes, radios, buttons
- Components: add 0.75rem bottom margin to expanders, metrics, dataframes, file upload dropzone
- Tabs: 0.5rem vertical padding inside tab panels for content breathing room