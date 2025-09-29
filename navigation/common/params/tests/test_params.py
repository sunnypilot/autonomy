import os

from navigation.common.params.params import Params


class TestParams:
    def setup_method(self):
        self.params = Params()

    def teardown_method(self):
        # Clean up test params
        test_keys = ["key", "other_key", "int_key", "list_key"]
        for key in test_keys:
            file_path = os.path.join(self.params.params_dir, key)
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_get_existing_key(self):
        self.params.put("key", "value")
        assert self.params.get("key") == "value"

    def test_get_nonexistent_key(self):
        assert self.params.get("nonexistent") is None

    def test_get_with_bytes_encoding(self):
        test_bytes = b"test bytes"
        self.params.put("key", test_bytes)
        result = self.params.get("key", encoding='bytes')
        assert result == test_bytes

    def test_get_mapbox_token(self):
        result = self.params.get('MapboxToken')
        assert isinstance(result, str) and len(result) == 90

    def test_get_other_key_utf8(self):
        self.params.put("other_key", "plain_value")
        result = self.params.get("other_key", encoding='utf8')
        assert result == "plain_value"

    def test_get_int_valid(self):
        self.params.put("key", "42")
        assert self.params.get_int("key") == 42

    def test_get_int_invalid(self):
        self.params.put("key", "not_a_number")
        assert self.params.get_int("key") == 0

    def test_get_int_none(self):
        assert self.params.get_int("nonexistent") == 0

    def test_put_string(self):
        self.params.put("key", "value")
        assert self.params.get("key") == "value"

    def test_put_bytes(self):
        test_bytes = b"test bytes"
        self.params.put("key", test_bytes)
        result = self.params.get("key", encoding='bytes')
        assert result == test_bytes

    def test_put_other_types(self):
        self.params.put("int_key", 42)
        assert self.params.get("int_key") == "42"
        self.params.put("list_key", [1, 2, 3])
        assert self.params.get("list_key") == "[1, 2, 3]"
