# Navigation Simulator

A debugging tool for simulating navigation along a route, updating GPS positions, and generating a map-based animation video.

## Getting Started

Run the simulator with a destination address:

```bash
python -m navigation.debug.nav_simulator --destination "Your Destination Address"
```

### Options

- `--destination`: Required. The destination address for navigation.

- `--gps-lat`: Initial GPS latitude (default: 34.23305).

- `--gps-lon`: Initial GPS longitude (default: -119.17557).

- `--interval`: Update interval in seconds (default: 0.01 for speed of simulation).

- `--output`: Output video file path (default: navigation/debug/simulation_videos/nav_simulation.mp4).

### Example

```bash
python -m navigation.debug.nav_simulator --destination "740 E Ventura Blvd. Camarillo, CA"
```

The simulator will print navigation updates and save an animation video.

### Glossary

- `lat`: latitude

- `lon`: longitude

- `haversine distance`: distance formula for calculating the distance between two points accounting for earths curvature. Matches real-world surface distance approximations better than flat distance formulas such as euclidean distance.

- `route geometry`: contains the coordinates needed for navigation

- `steps` these contain the instructions needed for each segment of the route. segments vary based on the api call and route distance. steps includes: 

        'maneuver': maneuver,
        'instruction': instruction,
        'distance': distance,
        'duration': duration,
        'location': location,
        'turn_direction': self.extract_turn_direction(instruction)

- 
