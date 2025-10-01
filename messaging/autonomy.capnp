@0x8d30477844c72468;
struct MapboxSettings {
  searchInput @0 :Int32;
  navData @1 :NavData;
  timestamp @2 :UInt64;
  lastGPSPosition @3 :GPSPosition;

  struct GPSPosition {
    longitude @0 :Float64;
    latitude @1 :Float64;
  }

  struct Destination {
    latitude @0 :Float64;
    longitude @1 :Float64;
    placeName @2 :Text;
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
    current @0 :Destination;
    route @1 :Route;
  }
}
