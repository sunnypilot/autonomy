@0xb779187b703db5aa;


struct MapboxSettings @0x8d30477844c72468 {
  searchInput @0 :Int32;
  navData @1 :NavData;
  timestamp @2 :UInt64;
  upcomingTurn @3 :Text;

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

struct LiveLocationKalman @0xe98c100195e6f0c0 {
  # These are the exact schemas that will be used on comma 3x device for livelocationkalman.
  positionECEF @0 : Measurement;
  positionGeodetic @1 : Measurement;
  velocityECEF @2 : Measurement;

  struct Measurement {
    value @0 : List(Float64);
    std @1 : List(Float64);
    valid @2 : Bool;
  }
}
