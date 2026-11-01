"""Independent integration and parser-contract evidence; Python stdlib only."""
import http.client
import json
import math
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request
from decimal import Decimal

from finite_json_boundary import (
    BoundaryError, MAX_BODY_BYTES, bounded_int, domain_value,
    finite_float, parse_body, start_loopback_server, strict_json,
)


class ApiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = start_loopback_server()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_port}/measure"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def send(self, content, content_type="application/json"):
        if isinstance(content, str):
            content = content.encode("utf-8")
        request = urllib.request.Request(
            self.endpoint, data=content, headers={"Content-Type": content_type},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_01_accepts_finite_numbers(self):
        self.assertEqual(self.send('{"value":1.25}'), (200, {"accepted": True, "value": 1.25}))
        self.assertEqual(self.send('{"value":-3e2}')[0], 200)

    def test_02_rejects_positive_and_negative_overflow(self):
        for token in ("1e999", "-1e999"):
            with self.subTest(token=token):
                status, response = self.send('{"value":' + token + '}')
                self.assertEqual(status, 400)
                self.assertIn("non-finite", response["error"])

    def test_03_rejects_nonstandard_literals(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token):
                status, response = self.send('{"value":' + token + '}')
                self.assertEqual(status, 400)
                self.assertIn("non-JSON", response["error"])

    def test_04_rejects_nested_overflow_before_domain_validation(self):
        status, response = self.send('{"value":5,"extras":{"samples":[1,1e999]}}')
        self.assertEqual(status, 400)
        self.assertIn("non-finite", response["error"])

    def test_05_rejects_unsafe_integers_and_duplicate_keys(self):
        for payload in ('{"value":9007199254740992}', '{"value":1,"value":2}'):
            self.assertEqual(self.send(payload)[0], 400)
        self.assertEqual(self.send('{"value":9007199254740991}')[0], 400) # domain limit

    def test_06_rejects_invalid_domain_types_and_ranges(self):
        for payload in ('{"value":true}', '{"value":null}', '{"value":1000001}', '{}', '[]'):
            self.assertEqual(self.send(payload)[0], 400)

    def test_07_rejects_oversized_and_non_utf8_input(self):
        self.assertEqual(self.send(b'{"value":0,"pad":"' + b'x' * MAX_BODY_BYTES + b'"}')[0], 413)
        self.assertEqual(self.send(b'\xff')[0], 400)

    def test_08_rejects_wrong_content_type_and_malformed_json(self):
        self.assertEqual(self.send('{"value":1}', content_type="text/plain")[0], 415)
        self.assertEqual(self.send('{"value":1')[0], 400)

    def test_09_strict_output_prevents_nonfinite_emission(self):
        for f in (math.nan, math.inf, -math.inf):
            with self.subTest(value=str(f)):
                with self.assertRaises(ValueError):
                    strict_json({"nested": [1, {"n": f}]})

    def test_10_underflow_is_finite_but_not_lossless(self):
        result = parse_body(b'{"value":1e-999}')
        self.assertEqual(result["value"], 0.0)
        self.assertNotEqual(Decimal('1e-999'), Decimal(str(result['value'])))

    def test_11_decimal_magnitude_is_preserved_but_not_serializable(self):
        obj = json.loads('{"value":1e999}', parse_float=Decimal)
        self.assertEqual(obj["value"], Decimal('1e999'))
        with self.assertRaises(TypeError):
            strict_json(obj)

    def test_12_large_integer_policy_separate_from_float_policy(self):
        self.assertEqual(bounded_int('9007199254740991'), 9007199254740991)
        with self.assertRaises(BoundaryError):
            bounded_int('9007199254740992')
        self.assertEqual(finite_float('1e308'), 1e308)

    def test_13_numpy_free_round_trip_through_real_http(self):
        for value in (0, -5, 3.125, 1e-10, 1000000):
            with self.subTest(value=value):
                status, response = self.send(json.dumps({"value": value}))
                self.assertEqual(status, 200)
                self.assertEqual(response["value"], value)

    def test_14_no_nonstandard_json_tokens_in_error_response(self):
        status, body = self.send('{"value":1e999}')
        self.assertEqual(status, 400)
        strict_bytes = strict_json(body)
        self.assertNotIn(b'Infinity', strict_bytes)
        self.assertNotIn(b'NaN', strict_bytes)

    def test_15_works_through_non_ascii_transport(self):
        self.assertEqual(self.send('{"value":1,"note":"café"}')[0], 200)


    def test_16_early_rejections_close_unread_body_before_next_request(self):
        cases = (
            ("/unknown", "application/json", b'{"value":1}', 404, True),
            ("/measure", "text/plain", b'{"value":1}', 415, True),
            ("/measure", "application/json", b'{"value":1}', 411, False),
            ("/measure", "application/json", b"x" * (MAX_BODY_BYTES + 1), 413, True),
        )
        for path, content_type, body, expected_status, send_length in cases:
            with self.subTest(status=expected_status):
                connection = http.client.HTTPConnection(
                    "127.0.0.1", self.server.server_port, timeout=3
                )
                try:
                    if send_length:
                        connection.request("POST", path, body=body,
                                           headers={"Content-Type": content_type})
                    else:
                        # http.client.request adds Content-Length automatically;
                        # manually construct an unframed body to exercise 411.
                        connection.putrequest("POST", path)
                        connection.putheader("Content-Type", content_type)
                        connection.endheaders(body)
                    response = connection.getresponse()
                    self.assertEqual(response.status, expected_status)
                    self.assertEqual(response.getheader("Connection"), "close")
                    self.assertTrue(response.will_close)
                    self.assertIn("error", json.loads(response.read()))

                    # A subsequent request on the same HTTPConnection object
                    # must reconnect, not parse the rejected body's bytes.
                    connection.request("POST", "/measure", body=b'{"value":2}',
                                       headers={"Content-Type": "application/json"})
                    next_response = connection.getresponse()
                    self.assertEqual(next_response.status, 200)
                    self.assertEqual(json.loads(next_response.read()),
                                     {"accepted": True, "value": 2})
                finally:
                    connection.close()

    def test_17_consumed_invalid_json_body_allows_keepalive(self):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=3
        )
        try:
            connection.request("POST", "/measure", body=b'{"value":',
                               headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            self.assertEqual(response.status, 400)
            self.assertFalse(response.will_close)
            response.read()
            sock = connection.sock
            self.assertIsNotNone(sock)

            connection.request("POST", "/measure", body=b'{"value":3}',
                               headers={"Content-Type": "application/json"})
            next_response = connection.getresponse()
            self.assertEqual(next_response.status, 200)
            self.assertEqual(json.loads(next_response.read()),
                             {"accepted": True, "value": 3})
            self.assertIs(connection.sock, sock)
        finally:
            connection.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)