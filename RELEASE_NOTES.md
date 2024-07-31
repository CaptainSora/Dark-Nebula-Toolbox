# Release Notes

All notable changes to this project will be documented in this file. See the About section at the end for details.


## [0.4.1] - 2024-07-30

### User Interface
- Updated text output to clearly display important information
- Added new user input to specify when the first genrich occurs
- Changed all times to display as a duration

### Visualizations
- Updated line chart x-axis to display time as a duration
- Added data from before the second genrich

### Simulation
- Updated simulation to use the start of the DRS as time zero


## [0.4.0] - 2024-07-16

### Visualizations
- Added a second tab for animated charts which automatically progress through time steps
    - Added two playback speed options


## [0.3.3] - 2024-07-14

### Visualizations
- Improved slider spacing to align with the line chart
- Improved line chart axis domains to use the full width and height
- Improved line chart vertical and horizontal overlay colors to stand out more


## [0.3.2] - 2024-07-14

### Visualizations
- Improved line chart to indicate the current time selected by the DRS Time slider
- Improved bar chart axis titles, y-axis domain, and y-axis ticks to be more readable


## [0.3.1] - 2024-07-14

### User Interface
- Added dynamic icon for the Miner Level user input to match the currently selected level
- Improved bar chart to be controllable by the DRS Time slider instead of animating on its own


## [0.3.0] - 2024-07-11

### User Interface
- Added version number and build date
- Clarified user input to specify Artifact Boosts

### Simulation
- Fixed a bug where target boosts were reached at the same time step as hydro ran out


## [0.2] - 2024-07-10

### User Interface
- Changed default values for user inputs to be useful sample values to see simulation results

### Visualizations
- Added an animated bar chart showing specific asteroid values at each time step

### Simulation
- Fixed a bug where the simulation would give up checking start times too soon

### Hosting
- Deployed [pre-release app](https://dn-toolbox.streamlit.app/) to Streamlit


## [0.1] - 2024-07-09

### User Interface
- Added user inputs for module levels with associated icons
- Added a button to run the simulation based on provided inputs
- Added a line chart showing the total hydro available throughout the DRS
- Added a slider to select a time step for future graphs

### Simulation
- Created proof-of-concept simulation to optimize mining duration

### Privacy
- Disabled Streamlit's browser data tracking


# About

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Instead of grouping changes by their type (which may be useful for developers), changes are instead grouped by feature. Types should be inferable from the first word of each item.

Versioning is sequence-based following the format major.minor\[.build\]:
- Major changes indicate a significant change such as a new page or tool independent from the others
- Minor changes indicate new features to existing pages or tools
- Builds indicate small changes such as an update to a feature and/or bug fixes