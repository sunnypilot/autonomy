@0x8d30477844c72468;
struct MapboxSettings {
  publicKey @0 :Text;
  lastGPSPosition @1 :GPSPosition;
  searchInput @2 :Int32;
  navData @3 :NavData;

  struct GPSPosition {
    longitude @0 :Float64;
    latitude @1 :Float64;
  }

  struct NavDestination {
    latitude @0 :Float64;
    longitude @1 :Float64;
    placeName @2 :Text;
  }

  struct NavDestinationEntry {
    latitude @0 :Float64;
    longitude @1 :Float64;
    placeName @2 :Text;
  }

  struct NavDestinationsList {
    entries @0 :List(NavDestinationEntry);
  }

  struct RouteStep {
    instruction @0 :Text;
    distance @1 :Float64;
    duration @2 :Float64;
    maneuver @3 :Text;
    location @4 :GPSPosition;
  }

  struct MaxSpeedEntry {
    speed @0 :Float64;
    unit @1 :Text;
  }

  struct Route {
    steps @0 :List(RouteStep);
    totalDistance @1 :Float64;
    totalDuration @2 :Float64;
    geometry @3 :List(GPSPosition);
    maxspeed @4 :List(MaxSpeedEntry);
  }

  struct NavData {
    current @0 :NavDestination;
    cache @1 :NavDestinationsList;
    route @2 :Route;
  }
}
