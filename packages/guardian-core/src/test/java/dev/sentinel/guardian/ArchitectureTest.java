package dev.sentinel.guardian;

import static org.junit.jupiter.api.Assertions.*;

import java.io.DataInputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import org.junit.jupiter.api.Test;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

class ArchitectureTest {
  @Test
  void productionStaticStateIsImmutable() throws Exception {
    try (Stream<Path> paths = Files.walk(Paths.get("target/classes"))) {
      for (Path file :
          paths.filter(p -> p.toString().endsWith(".class")).collect(Collectors.toList())) {
        String name =
            Paths.get("target/classes")
                .relativize(file)
                .toString()
                .replace('\\', '.')
                .replace('/', '.')
                .replaceAll("\\.class$", "");
        Class<?> type = Class.forName(name, false, getClass().getClassLoader());
        for (java.lang.reflect.Field field : type.getDeclaredFields()) {
          if (!field.isSynthetic() && java.lang.reflect.Modifier.isStatic(field.getModifiers())) {
            assertTrue(
                java.lang.reflect.Modifier.isFinal(field.getModifiers()),
                name + "." + field.getName());
            assertTrue(
                field.getType().isPrimitive()
                    || field.getType() == String.class
                    || field.getType().isEnum(),
                name + ": mutable static reference");
          }
        }
      }
    }
  }

  @Test
  void everyProductionClassUsesJava8Bytecode() throws Exception {
    try (Stream<Path> paths = Files.walk(Paths.get("target/classes"))) {
      List<Path> classes =
          paths.filter(p -> p.toString().endsWith(".class")).collect(Collectors.toList());
      assertFalse(classes.isEmpty(), "Missing compiled core");
      for (Path file : classes) {
        try (DataInputStream input = new DataInputStream(Files.newInputStream(file))) {
          assertEquals(0xCAFEBABE, input.readInt());
          input.readUnsignedShort();
          assertEquals(52, input.readUnsignedShort(), file.toString());
        }
      }
    }
  }

  @Test
  void productionImportsRemainFrameworkFreeAndAlgorithmsDoNotReadClocks() throws Exception {
    Pattern imports = Pattern.compile("(?m)^import (?:static )?([^;]+);");
    try (Stream<Path> paths = Files.walk(Paths.get("src/main/java"))) {
      List<Path> sources =
          paths.filter(p -> p.toString().endsWith(".java")).collect(Collectors.toList());
      assertFalse(sources.isEmpty());
      for (Path file : sources) {
        String source = new String(Files.readAllBytes(file), StandardCharsets.UTF_8);
        Matcher matcher = imports.matcher(source);
        while (matcher.find()) {
          String name = matcher.group(1);
          assertTrue(
              name.startsWith("java.lang.")
                  || name.startsWith("java.util.")
                  || name.startsWith("dev.sentinel.guardian."),
              file + ": forbidden import " + name);
        }
        assertFalse(source.contains("System."), file + ": core must not read clocks or perform IO");
        assertFalse(source.contains("java.time."), file + ": no clock API in algorithms");
        assertFalse(source.contains("java.util.concurrent"), file + ": no background execution");
        assertFalse(source.contains("new Thread"), file + ": no core-owned threads");
        assertFalse(source.contains("Thread.sleep"), file + ": no timing sleeps");
      }
    }
  }

  @Test
  void moduleHasNoParentOrRuntimeDependencies() throws Exception {
    DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
    factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
    factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
    factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
    Element project =
        factory.newDocumentBuilder().parse(Paths.get("pom.xml").toFile()).getDocumentElement();
    assertEquals(0, project.getElementsByTagName("parent").getLength());
    NodeList dependencies = project.getElementsByTagName("dependency");
    for (int i = 0; i < dependencies.getLength(); i++) {
      Element dependency = (Element) dependencies.item(i);
      NodeList scopes = dependency.getElementsByTagName("scope");
      assertEquals(1, scopes.getLength(), "Every dependency must be test-only");
      assertEquals("test", scopes.item(0).getTextContent().trim());
    }
  }
}
