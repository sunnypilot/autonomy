@0xb779187b703db5aa;


struct MapboxSettings @0x8d30477844c72468 {
  timestamp @0 :UInt64;
  upcomingTurn @1 :Text;
  currentSpeedLimit @2 :Float64;
  bannerInstructions @3 :Text;
  distanceToNextTurn @4 :Float64;
  routeProgressPercent @5 :Float64;
  distanceFromRoute @6 :Float64;
  routePositionCumulative @7 :Float64;
  distanceToEndOfStep @8 :Float64;
  totalDistanceRemaining @9 :Float64;
  totalTimeRemaining @10 :Float64;
  allManeuvers @11 :List(Maneuver);
  speedLimitSign @12 :Text;
}

struct Maneuver @0x9f8b7c6d5e4f3a2b {
  distance @0 :Float64;
  type @1 :Text;
  modifier @2 :Text;
}

struct LiveLocationKalman @0xe98c100195e6f0c0 {
  # These are the exact schemas that will be used on comma 3x device for livelocationkalman.
  positionECEF @0 : Measurement;
  positionGeodetic @1 : Measurement;
  velocityECEF @2 : Measurement;
  calibratedOrientationNED @3 : Measurement;

  struct Measurement {
    value @0 : List(Float64);
    std @1 : List(Float64);
    valid @2 : Bool;
  }
}
