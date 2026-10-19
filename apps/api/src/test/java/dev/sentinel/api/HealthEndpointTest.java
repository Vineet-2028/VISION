package dev.sentinel.api;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class HealthEndpointTest {
  @Autowired private MockMvc mvc;

  @ParameterizedTest
  @ValueSource(strings = {"/health/live", "/health/ready"})
  void healthEndpointsHonorTheContract(String path) throws Exception {
    mvc.perform(get(path))
        .andExpect(status().isOk())
        .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
        .andExpect(jsonPath("$.status").value("ok"))
        .andExpect(jsonPath("$.service").value("sentinel-api"))
        .andExpect(jsonPath("$.length()").value(2));
  }

  @Test
  void unknownRouteIsNotAHealthSuccess() throws Exception {
    mvc.perform(get("/missing")).andExpect(status().isNotFound());
  }
}
