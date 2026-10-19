package dev.sentinel.guardian;

import static dev.sentinel.guardian.GeometryFixtures.*;
import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.OptionalDouble;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class SpatialGeometryTest {
  private static Vector3 world(double x, double y, double z) {
    return new Vector3(W, x, y, z);
  }

  private static DevicePoseEstimate pose(Quaternion rotation, Vector3 translation) {
    return new DevicePoseEstimate(
        TIME,
        Optional.of(new RigidTransform(D, W, rotation, translation)),
        new Confidence(.8),
        OptionalDouble.of(.1),
        OptionalDouble.of(.02));
  }

  private static CameraExtrinsics extrinsics(Quaternion rotation, Vector3 translation) {
    return new CameraExtrinsics(ID, "extrinsics1", new RigidTransform(C, D, rotation, translation));
  }

  private static Ray3D ray(Vector3 origin, Vector3 direction) {
    return new Ray3D(origin, direction, Optional.of(TIME));
  }

  private static GroundPlaneEstimate ground() {
    return new GroundPlaneEstimate(
        Optional.of(new Plane3D(world(0, 0, 0), world(0, 0, 1))),
        TIME,
        new Confidence(.9),
        OptionalDouble.of(.05),
        OptionalDouble.of(.01),
        "synthetic-test-plane");
  }

  @Test
  void raysHaveMetricParameterAndRejectNegativeDistance() {
    Ray3D ray = ray(world(1, 2, 3), world(0, 0, -2));
    MathTest.xyz(ray.pointAt(2), 1, 2, 1);
    assertEquals(1, ray.direction().magnitude());
    assertThrows(IllegalArgumentException.class, () -> ray.pointAt(-1));
    assertThrows(IllegalArgumentException.class, () -> ray.pointAt(Double.POSITIVE_INFINITY));
    assertThrows(IllegalArgumentException.class, () -> ray(world(0, 0, 0), world(0, 0, 0)));
  }

  @Test
  void planeSignedDistanceAndProjection() {
    Plane3D plane = new Plane3D(world(0, 0, 2), world(0, 0, 4));
    assertEquals(3, plane.signedDistance(world(1, 2, 5)));
    assertEquals(-1, plane.signedDistance(world(1, 2, 1)));
    MathTest.xyz(plane.projectPoint(world(1, 2, 5)), 1, 2, 2);
    Plane3D tilted = new Plane3D(world(0, 0, 0), world(0, 1, 1));
    assertEquals(StrictMath.sqrt(2), tilted.signedDistance(world(0, 1, 1)), 1e-10);
    MathTest.xyz(tilted.projectPoint(world(0, 1, 1)), 0, 0, 0);
  }

  @ParameterizedTest
  @CsvSource({
    "0,0,2,0,0,-1,true,0,0,0",
    "0,0,2,1,0,-1,true,2,0,0",
    "0,0,2,1,0,0,false,0,0,0",
    "0,0,2,0,0,1,false,0,0,0",
    "1,2,0,0,0,1,true,1,2,0",
    "0,0,2,1,0,-0.00000000000001,false,0,0,0"
  })
  void rayPlaneCases(
      double ox,
      double oy,
      double oz,
      double dx,
      double dy,
      double dz,
      boolean valid,
      double x,
      double y,
      double z) {
    Optional<Vector3> hit =
        ground().plane().get().rayIntersection(ray(world(ox, oy, oz), world(dx, dy, dz)), POLICY);
    assertEquals(valid, hit.isPresent());
    if (valid) MathTest.xyz(hit.get(), x, y, z);
  }

  @Test
  void worldRayAppliesTranslationOnlyToOrigin() {
    CameraExtrinsics e = extrinsics(Quaternion.identity(), new Vector3(D, .05, .02, .01));
    Ray3D result =
        SpatialGeometry.pixelToWorldRay(
                pixel(500, 500), frame(), model(), e, pose(Quaternion.identity(), world(2, 3, 1.5)))
            .get();
    MathTest.xyz(result.origin(), 2.05, 3.02, 1.51);
    MathTest.xyz(result.direction(), 0, 0, 1);
    assertEquals(W, result.frame());
    assertEquals(TIME, result.time().get());
  }

  @Test
  void rotatedDeviceAndNonzeroCameraTranslation() {
    CameraExtrinsics e = extrinsics(new Quaternion(1, 0, 1, 0), new Vector3(D, .1, 0, 0));
    Ray3D result =
        SpatialGeometry.pixelToWorldRay(
                pixel(500, 500),
                frame(),
                model(),
                e,
                pose(new Quaternion(1, 0, 0, 1), world(2, 3, 1)))
            .get();
    MathTest.xyz(result.origin(), 2, 3.1, 1);
    MathTest.xyz(result.direction(), 0, 1, 0);
  }

  @Test
  void downwardCameraGroundAndSidewaysCamera() {
    CameraExtrinsics down = extrinsics(new Quaternion(0, 1, 0, 0), new Vector3(D, .1, 0, 0));
    Ray3D ray =
        SpatialGeometry.pixelToWorldRay(
                pixel(500, 500),
                frame(),
                model(),
                down,
                pose(Quaternion.identity(), world(0, 0, 1.5)))
            .get();
    GroundIntersectionCandidate candidate =
        SpatialGeometry.groundIntersection(ray, ground(), POLICY).get();
    MathTest.xyz(candidate.nominalPoint(), .1, 0, 0);
    assertSame(ray, candidate.ray());
    assertEquals(.05, candidate.ground().offsetStdMeters().getAsDouble());
    CameraExtrinsics side = extrinsics(new Quaternion(1, 0, 1, 0), new Vector3(D, 0, 0, 0));
    Ray3D sideways =
        SpatialGeometry.pixelToWorldRay(
                pixel(500, 500),
                frame(),
                model(),
                side,
                pose(Quaternion.identity(), world(0, 0, 1.5)))
            .get();
    assertFalse(SpatialGeometry.groundIntersection(sideways, ground(), POLICY).isPresent());
  }

  @Test
  void tiltedCameraIntersectionIsAnalytical() {
    double half = 3 * StrictMath.PI / 8;
    CameraExtrinsics e =
        extrinsics(
            new Quaternion(StrictMath.cos(half), StrictMath.sin(half), 0, 0),
            new Vector3(D, 0, 0, 0));
    Ray3D ray =
        SpatialGeometry.pixelToWorldRay(
                pixel(500, 500), frame(), model(), e, pose(Quaternion.identity(), world(0, 0, 2)))
            .get();
    MathTest.xyz(
        SpatialGeometry.groundIntersection(ray, ground(), POLICY).get().nominalPoint(), 0, -2, 0);
  }

  @Test
  void unknownPoseAndGroundAreUnavailable() {
    DevicePoseEstimate unknown =
        new DevicePoseEstimate(
            TIME,
            Optional.empty(),
            new Confidence(0),
            OptionalDouble.empty(),
            OptionalDouble.empty());
    assertFalse(
        SpatialGeometry.pixelToWorldRay(
                pixel(500, 500),
                frame(),
                model(),
                extrinsics(Quaternion.identity(), new Vector3(D, 0, 0, 0)),
                unknown)
            .isPresent());
    GroundPlaneEstimate unknownGround =
        new GroundPlaneEstimate(
            Optional.empty(),
            TIME,
            new Confidence(0),
            OptionalDouble.empty(),
            OptionalDouble.empty(),
            "unknown");
    assertFalse(
        SpatialGeometry.groundIntersection(
                ray(world(0, 0, 1), world(0, 0, -1)), unknownGround, POLICY)
            .isPresent());
  }

  @Test
  void identitiesTimesAndFrameChainsAreChecked() {
    CameraExtrinsics wrong =
        new CameraExtrinsics(
            new CalibrationId("front", "cal1"),
            "e1",
            new RigidTransform(C, D, Quaternion.identity(), new Vector3(D, 0, 0, 0)));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            SpatialGeometry.pixelToWorldRay(
                pixel(500, 500),
                frame(),
                model(),
                wrong,
                pose(Quaternion.identity(), world(0, 0, 1))));
    DevicePoseEstimate stale =
        new DevicePoseEstimate(
            new MonotonicTime("sensor", 999),
            pose(Quaternion.identity(), world(0, 0, 1)).transform(),
            new Confidence(1),
            OptionalDouble.empty(),
            OptionalDouble.empty());
    assertThrows(
        IllegalArgumentException.class,
        () ->
            SpatialGeometry.pixelToWorldRay(
                pixel(500, 500),
                frame(),
                model(),
                extrinsics(Quaternion.identity(), new Vector3(D, 0, 0, 0)),
                stale));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            ground()
                .plane()
                .get()
                .rayIntersection(
                    new Ray3D(camera(0, 0, 1), camera(0, 0, -1), Optional.of(TIME)), POLICY));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new CameraExtrinsics(
                ID, "e", new RigidTransform(D, W, Quaternion.identity(), world(0, 0, 0))));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            SpatialGeometry.groundIntersection(
                new Ray3D(world(0, 0, 1), world(0, 0, -1), Optional.empty()), ground(), POLICY));
  }

  @Test
  void sharedCalibrationIsSafeForConcurrentReads() throws Exception {
    CameraModel shared = model(intrinsics(), new BrownConradyDistortion(.1, 0, 0, .001, 0, 2));
    ExecutorService pool = Executors.newFixedThreadPool(4);
    try {
      List<Future<Double>> results = new ArrayList<>();
      for (int i = 0; i < 32; i++)
        results.add(
            pool.submit(() -> shared.bearing(pixel(800, 600), frame()).get().azimuthRadians()));
      double expected = results.get(0).get();
      for (Future<Double> result : results) assertEquals(expected, result.get(), 0.0);
    } finally {
      pool.shutdownNow();
    }
  }
}
