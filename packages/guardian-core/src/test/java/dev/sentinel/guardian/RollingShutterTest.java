package dev.sentinel.guardian;

import static dev.sentinel.guardian.TemporalFixtures.*;
import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class RollingShutterTest {
  private static ImageSize image() {
    return new ImageSize(new FrameId(FrameKind.IMAGE, "sensor"), 5, 5);
  }

  @Test
  void forwardAndReverseRowMidpoints() {
    RollingShutterModel top =
        new RollingShutterModel(
            RollingShutterModel.Kind.ROLLING_SHUTTER,
            image(),
            time(100),
            40,
            RollingShutterModel.Scan.TOP_TO_BOTTOM);
    assertEquals(100, top.timestampForImageRow(image().frame(), .5).get().nanos());
    assertEquals(120, top.timestampForImageRow(image().frame(), 2.5).get().nanos());
    assertEquals(140, top.timestampForImageRow(image().frame(), 4.5).get().nanos());
    assertEquals(120, top.frameMidpoint().get().nanos());
    RollingShutterModel bottom =
        new RollingShutterModel(
            RollingShutterModel.Kind.ROLLING_SHUTTER,
            image(),
            time(100),
            40,
            RollingShutterModel.Scan.BOTTOM_TO_TOP);
    assertEquals(140, bottom.timestampForImageRow(image().frame(), .5).get().nanos());
    assertEquals(100, bottom.timestampForImageRow(image().frame(), 4.5).get().nanos());
  }

  @Test
  void globalUnknownAndSingleRow() {
    RollingShutterModel global =
        new RollingShutterModel(
            RollingShutterModel.Kind.GLOBAL_SHUTTER,
            image(),
            time(42),
            0,
            RollingShutterModel.Scan.TOP_TO_BOTTOM);
    assertEquals(42, global.timestampForImageRow(image().frame(), 4.5).get().nanos());
    RollingShutterModel unknown =
        new RollingShutterModel(
            RollingShutterModel.Kind.UNKNOWN,
            image(),
            time(42),
            0,
            RollingShutterModel.Scan.TOP_TO_BOTTOM);
    assertFalse(unknown.timestampForImageRow(image().frame(), 2.5).isPresent());
    assertFalse(unknown.frameMidpoint().isPresent());
    RollingShutterModel single =
        new RollingShutterModel(
            RollingShutterModel.Kind.ROLLING_SHUTTER,
            new ImageSize(image().frame(), 1, 1),
            time(0),
            0,
            RollingShutterModel.Scan.BOTTOM_TO_TOP);
    assertEquals(0, single.timestampForImageRow(image().frame(), .5).get().nanos());
  }

  @Test
  void boundsFramesAndTimestampOverflow() {
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new RollingShutterModel(
                RollingShutterModel.Kind.ROLLING_SHUTTER,
                image(),
                time(Long.MAX_VALUE),
                1,
                RollingShutterModel.Scan.TOP_TO_BOTTOM));
    RollingShutterModel model =
        new RollingShutterModel(
            RollingShutterModel.Kind.ROLLING_SHUTTER,
            image(),
            time(Long.MAX_VALUE - 40),
            40,
            RollingShutterModel.Scan.TOP_TO_BOTTOM);
    assertEquals(Long.MAX_VALUE, model.timestampForImageRow(image().frame(), 4.5).get().nanos());
    assertThrows(
        IllegalArgumentException.class, () -> model.timestampForImageRow(image().frame(), 0));
    assertThrows(
        IllegalArgumentException.class,
        () -> model.timestampForImageRow(image().frame(), Double.NaN));
    assertThrows(
        IllegalArgumentException.class,
        () -> model.timestampForImageRow(new FrameId(FrameKind.IMAGE, "rotated"), 2));
  }
}
