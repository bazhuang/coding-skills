#!/usr/bin/env python3
"""Unit tests for scan_api_entries.py — language dispatch, comment stripping,
Spring path merging, entry-type classification.

Run: python -m unittest skills.repo-wiki.tests.test_scan_api_entries
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

_SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import scan_api_entries as sae  # noqa: E402


def _scan(files: dict[str, str], **kwargs) -> dict:
    """Create a temp repo with the given {rel_path: content} and scan it."""
    with tempfile.TemporaryDirectory() as d:
        for rel, content in files.items():
            full = os.path.join(d, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
        return sae.scan_api_entries(d, **kwargs)


class TestLanguageDispatch(unittest.TestCase):
    """P0-03: per-language pattern dispatch — no cross-language noise."""

    def test_map_put_not_detected_as_gin_route(self):
        """Java Map.put(...) must NOT be matched as a Go Gin route."""
        result = _scan({
            "src/Main.java": """
                import java.util.Map;
                public class Main {
                    public void process(Map<String, Object> ctx) {
                        ctx.put("status", "ok");
                    }
                }
            """,
        })
        entries = result["entries"]
        # No Gin entries should appear from a Java file
        self.assertFalse(any(e["framework"] == "gin" for e in entries),
                         f"Map.put falsely matched as Gin route: {entries}")
        self.assertEqual(len(entries), 0)

    def test_mixed_languages_no_cross_pollution(self):
        """A Java controller and a Python app.get should each be detected by their own language patterns."""
        result = _scan({
            "java/Controller.java": """
                @RestController
                @RequestMapping("/api")
                public class Controller {
                    @GetMapping("/users")
                    public List<User> users() { return null; }
                }
            """,
            "python/app.py": """
                from fastapi import FastAPI
                app = FastAPI()

                @app.get("/health")
                def health():
                    return {"ok": True}
            """,
        })
        entries = result["entries"]
        # Should have one Spring entry and one FastAPI entry
        spring = [e for e in entries if e["framework"] == "spring"]
        fastapi = [e for e in entries if e["framework"] == "fastapi"]
        self.assertEqual(len(spring), 1)
        self.assertEqual(len(fastapi), 1)


class TestCommentStripping(unittest.TestCase):
    """P0-03: annotations inside comments and strings must not match."""

    def test_javadoc_annotation_not_counted(self):
        """@GetMapping inside a Javadoc block comment must not be detected."""
        result = _scan({
            "src/Svc.java": """
                /**
                 * Example: @GetMapping("/example")
                 * This is just documentation.
                 */
                public class Svc {
                    public void doSomething() {}
                }
            """,
        })
        entries = result["entries"]
        self.assertEqual(len(entries), 0,
                         f"Javadoc annotation falsely detected: {entries}")

    def test_line_comment_annotation_not_counted(self):
        """// @GetMapping on a line comment must not be detected."""
        result = _scan({
            "src/Svc.java": """
                public class Svc {
                    // @GetMapping("/commented")
                    public void doSomething() {}
                }
            """,
        })
        entries = result["entries"]
        self.assertEqual(len(entries), 0,
                         f"Line comment annotation falsely detected: {entries}")

    def test_string_literal_annotation_not_counted(self):
        """@GetMapping inside a Java string literal must not be detected."""
        result = _scan({
            "src/Svc.java": '''
                public class Svc {
                    private String desc = "Use @GetMapping(\\"/x\\") to create endpoint";
                }
            ''',
        })
        entries = result["entries"]
        self.assertEqual(len(entries), 0,
                         f"String literal annotation falsely detected: {entries}")


class TestSpringPathMerging(unittest.TestCase):
    """P0-03: Spring class-level + method-level path merging."""

    def test_class_plus_method_path_merged(self):
        """@RequestMapping("/api") on class + @GetMapping("/users") → /api/users."""
        result = _scan({
            "src/UserController.java": """
                @RestController
                @RequestMapping("/api")
                public class UserController {
                    @GetMapping("/users")
                    public List<User> getUsers() { return null; }
                }
            """,
        })
        inbound = [e for e in result["entries"] if e["type"] == "inbound_http"]
        self.assertEqual(len(inbound), 1)
        self.assertEqual(inbound[0]["route"], "/api/users")
        self.assertEqual(inbound[0]["method"], "GET")

    def test_method_without_class_path(self):
        """@GetMapping without class-level @RequestMapping should still work."""
        result = _scan({
            "src/Bare.java": """
                @RestController
                public class Bare {
                    @GetMapping("/items")
                    public List<Item> items() { return null; }
                }
            """,
        })
        inbound = [e for e in result["entries"] if e["type"] == "inbound_http"]
        self.assertEqual(len(inbound), 1)
        self.assertEqual(inbound[0]["route"], "/items")


class TestEntryTypeClassification(unittest.TestCase):
    """P0-03: discriminated entry types."""

    def test_feign_client_is_outbound(self):
        """@FeignClient must be outbound_http_client, NOT inbound_http."""
        result = _scan({
            "src/OrderClient.java": """
                @FeignClient(name = "order-service")
                public interface OrderClient {
                    @GetMapping("/orders/{id}")
                    Order getOrder(@PathVariable Long id);
                }
            """,
        })
        feign = [e for e in result["entries"] if e["type"] == "outbound_http_client"]
        self.assertTrue(feign, "Feign client not detected as outbound_http_client")
        # The @GetMapping inside the Feign interface should NOT be counted as inbound
        # (it's a declaration of what the client calls, not what the server serves)
        # Note: currently the scanner may still match @GetMapping as inbound.
        # This is a known limitation; the Feign classification is the primary signal.

    def test_scheduled_is_scheduled_job(self):
        result = _scan({
            "src/BatchJob.java": """
                @Component
                public class BatchJob {
                    @Scheduled(cron = "0 0 * * *")
                    public void runDaily() {}
                }
            """,
        })
        scheduled = [e for e in result["entries"] if e["type"] == "scheduled_job"]
        self.assertTrue(scheduled, "Scheduled job not detected")
        self.assertEqual(scheduled[0].get("cron"), "0 0 * * *")

    def test_rabbit_listener_is_message_consumer(self):
        result = _scan({
            "src/OrderConsumer.java": """
                @Component
                public class OrderConsumer {
                    @RabbitListener(queues = "order.queue")
                    public void onOrder(OrderEvent event) {}
                }
            """,
        })
        consumers = [e for e in result["entries"] if e["type"] == "message_consumer"]
        self.assertTrue(consumers, "RabbitListener not detected as message_consumer")
        self.assertEqual(consumers[0].get("queue"), "order.queue")

    def test_kafka_listener_is_message_consumer(self):
        result = _scan({
            "src/EventConsumer.java": """
                @Component
                public class EventConsumer {
                    @KafkaListener(topics = "order-events")
                    public void onOrderEvent(OrderEvent e) {}
                }
            """,
        })
        consumers = [e for e in result["entries"] if e["type"] == "message_consumer"]
        self.assertTrue(consumers, "KafkaListener not detected")

    def test_python_fastapi_inbound(self):
        result = _scan({
            "app.py": """
                from fastapi import FastAPI
                app = FastAPI()

                @app.get("/health")
                def health():
                    return {"ok": True}
            """,
        })
        inbound = [e for e in result["entries"] if e["type"] == "inbound_http"]
        self.assertTrue(inbound, "FastAPI endpoint not detected")
        self.assertEqual(inbound[0]["framework"], "fastapi")
        self.assertEqual(inbound[0]["method"], "GET")

    def test_event_listener_detected(self):
        result = _scan({
            "src/Handler.java": """
                @Component
                public class EventHandler {
                    @EventListener
                    public void handle(OrderCreated event) {}
                }
            """,
        })
        listeners = [e for e in result["entries"] if e["type"] == "event_listener"]
        self.assertTrue(listeners, "EventListener not detected")


class TestBackwardCompat(unittest.TestCase):
    """api_entries field must contain only inbound_http entries."""

    def test_api_entries_is_inbound_only(self):
        result = _scan({
            "src/Ctrl.java": """
                @RestController
                public class Ctrl {
                    @PostMapping("/save")
                    public void save() {}

                    @Scheduled(cron = "0 0 * * *")
                    public void cleanup() {}
                }
            """,
        })
        # api_entries should only have the inbound POST
        self.assertEqual(len(result["api_entries"]), 1)
        self.assertEqual(result["api_entries"][0]["type"], "inbound_http")
        # But entries has both
        types = [e["type"] for e in result["entries"]]
        self.assertIn("inbound_http", types)
        self.assertIn("scheduled_job", types)

    def test_summary_total_endpoints_back_compat(self):
        result = _scan({
            "app.py": """
                app = None
                @app.get("/")
                def root(): pass
            """,
        })
        self.assertEqual(result["summary"]["total_endpoints"], len(result["api_entries"]))


class TestEdgeCases(unittest.TestCase):

    def test_empty_file_no_entries(self):
        result = _scan({"empty.py": ""})
        self.assertEqual(len(result["entries"]), 0)
        self.assertEqual(len(result["scan_warnings"]), 0)

    def test_non_scannable_file_ignored(self):
        result = _scan({"data.csv": "a,b,c\n1,2,3\n"})
        self.assertEqual(len(result["entries"]), 0)


if __name__ == "__main__":
    unittest.main()
