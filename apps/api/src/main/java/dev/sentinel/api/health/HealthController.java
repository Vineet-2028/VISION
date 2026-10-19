package dev.sentinel.api.health;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
  /** Readiness covers the current stateless routes; no data service is consumed yet. */
  @GetMapping({"/health/live", "/health/ready"})
  public HealthResponse health() {
    return new HealthResponse("ok", "sentinel-api");
  }
}
