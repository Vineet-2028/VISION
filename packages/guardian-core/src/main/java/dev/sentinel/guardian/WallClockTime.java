package dev.sentinel.guardian;

/** Unix epoch milliseconds for session/history metadata only; no motion arithmetic. */
public final class WallClockTime {
  private final long epochMillis;

  public WallClockTime(long epochMillis) {
    this.epochMillis = epochMillis;
  }

  public long epochMillis() {
    return epochMillis;
  }
}
