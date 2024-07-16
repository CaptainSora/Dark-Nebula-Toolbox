# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Versioning is sequence-based following the format major.minor\[.build\[.revision\]\]:
- Minor changes constitute a section of software or a feature
- Builds constitute changes within such a section or feature (which may include bug fixes)
- Revisions constitute non-critical bug fixes or similarly sized changes.


## [0.4.0] - 2024-07-16

### Added
- CHANGELOG.md file
- Second tab with animated charts (bar and line)
    - Identical to interactive charts
    - Two animation speeds


## [0.3.3] - 2024-07-11

### Changed
- Improved slider spacing to align with line chart widths
- Improved line chart axis domains


## [0.3.2] - 2024-07-11

### Added
- Line chart for total hydro values using Altair
    - Added responsive vline which syncs with time slider and bar chart

### Changed
- Bar chart axis titles, domains, and ticks changed to be more informative

### Removed
- Streamlit line chart


## [0.3.1] - 2024-07-11

### Added
- Dynamic image switching for Miner Level input
- Bar chart for asteroid values using Altair

### Removed
- Plotly bar chart


## [0.3.0] - 2024-07-11

### Added
- Version number and build date in-app

### Fixed
- Improved logging for a previously silent simulation fail state
- Simulation runs properly reset initial conditions
- Simulation properly handles race condition between completion and failure states
- Improved input label to specify Artifact Boosts


## [0.2] - 2024-07-10

### Added
- Plotly animated bar chart for asteroid values
- Default values set for inputs

### Fixed
- Increased the upper limit for delay values checked
- Improved simulation logging for initial conditions

### Changed
- App is now publicly available and hosted on Streamlit


## [0.1] - 2024-07-09

### Added
- Streamlit frontend
- Player module level inputs with game images
- Basic miner simulation
- Streamlit data tracking disabled
- Streamlit line chart for total hydro values
- Streamlit slider for drs time